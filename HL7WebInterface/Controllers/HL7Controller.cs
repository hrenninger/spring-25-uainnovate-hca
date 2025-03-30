using HL7WebInterface.Models;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

public class HL7Controller : Controller
{
    private readonly HL7Service _hl7Service;
    private readonly IWebHostEnvironment _webHostEnvironment;
    private static List<HL7Message> _messages = new List<HL7Message>();
    private const int PageSize = 100;

    public HL7Controller(HL7Service hl7Service, IWebHostEnvironment webHostEnvironment)
    {
        _hl7Service = hl7Service;
        _webHostEnvironment = webHostEnvironment;
    }

    public IActionResult Index(int page = 1, string sortColumn = "DateTime", string sortOrder = "asc")
    {
        if (_messages == null || !_messages.Any())
        {
            LoadAllHL7Files();
        }

        // Always start with a fresh full dataset
        IEnumerable<HL7Message> sortedMessages = _messages.AsEnumerable();

        // Apply sorting before pagination
        sortedMessages = sortColumn switch
        {
            "Id" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.Id) : sortedMessages.OrderByDescending(m => m.Id),
            "DateTime" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.DateTime) : sortedMessages.OrderByDescending(m => m.DateTime),
            "MRN" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.MRN) : sortedMessages.OrderByDescending(m => m.MRN),
            "LastName" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.LastName) : sortedMessages.OrderByDescending(m => m.LastName),
            "FirstName" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.FirstName) : sortedMessages.OrderByDescending(m => m.FirstName),
            "Facility" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.Facility) : sortedMessages.OrderByDescending(m => m.Facility),
            "MessageType" => sortOrder == "asc" ? sortedMessages.OrderBy(m => m.MSH9) : sortedMessages.OrderByDescending(m => m.MSH9),
            _ => sortedMessages
        };

        // Apply pagination AFTER sorting
        int totalMessages = sortedMessages.Count();
        var pagedMessages = sortedMessages.Skip((page - 1) * PageSize).Take(PageSize).ToList();

        ViewBag.CurrentPage = page;
        ViewBag.TotalPages = (int)Math.Ceiling((double)totalMessages / PageSize);
        ViewBag.SortColumn = sortColumn;
        ViewBag.SortOrder = sortOrder;

        return View(pagedMessages);
    }

    public IActionResult LoadHL7File()
    {
        LoadAllHL7Files();
        return RedirectToAction("Index");
    }

    private void LoadAllHL7Files()
    {
        string rawFilePath = Path.Combine(_webHostEnvironment.ContentRootPath, "Data", "deidentified_messages_sorted.txt");
        string redactedFilePath = Path.Combine(_webHostEnvironment.ContentRootPath, "Data", "messages_sorted.txt");

        if (System.IO.File.Exists(rawFilePath))
        {
            _messages = HL7Service.ParseHL7File(rawFilePath);

            // Load redacted messages
            if (System.IO.File.Exists(redactedFilePath))
            {
                HL7Service.LoadRedactedMessages(redactedFilePath);
            }
        }
    }

    public ActionResult Details(string mrn, string facility)
    {
        LoadAllHL7Files();

        // Find all messages with the same MRN and Facility
        var matchingMessages = _messages
            .Where(m => m.MRN == mrn && m.Facility == facility)
            .ToList();

        if (!matchingMessages.Any())
        {
            return NotFound();  // Handle case where no matching messages exist
        }

        ViewBag.MRN = mrn;
        ViewBag.Facility = facility;
        return View(matchingMessages); // Pass list of matching messages to the view
    }


    [HttpGet]
public IActionResult GetRedactedMessage(int id)
{
    // Get the raw redacted message as string
    string redactedMessageText = HL7Service.GetRedactedMessage(id);
    
    // Create a model that mimics the structure used in the raw message templates
    var message = new HL7Message { Id = id };
    var segments = new List<HL7Segment>();
    
    // Split the raw message into segments (by newlines)
    string[] segmentLines = redactedMessageText.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
    int segmentSequence = 0;
    
    foreach (var segmentLine in segmentLines)
    {
        if (string.IsNullOrWhiteSpace(segmentLine))
            continue;
            
        // Split the segment into fields (by pipe character)
        string[] fieldValues = segmentLine.Split('|');
        string segmentType = fieldValues.Length > 0 ? fieldValues[0] : "Unknown";
        
        var segment = new HL7Segment
        {
            HL7Message = message,
            SegmentType = segmentType,
            Sequence = segmentSequence++,
            Fields = new List<HL7Field>()
        };
        
        // Parse fields within segment
        for (int i = 1; i < fieldValues.Length; i++)
        {
            segment.Fields.Add(new HL7Field
            {
                HL7Segment = segment,
                FieldLabel = $"{segmentType}-{i}",
                Value = fieldValues[i],
                FieldPosition = i
            });
        }
        
        segments.Add(segment);
    }
    
    message.Segments = segments;
    
    // Return the view as HTML rather than JSON
    return PartialView("_RedactedMessagePartial", message);
}
}