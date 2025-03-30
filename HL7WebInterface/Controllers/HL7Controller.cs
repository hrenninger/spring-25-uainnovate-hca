using HL7WebInterface.Models;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using System.IO;
using System.Linq;

public class HL7Controller : Controller
{
    private readonly HL7Service _hl7Service;
    private readonly IWebHostEnvironment _webHostEnvironment;
    private static List<HL7Message> _messages = new List<HL7Message>();

    private const int PageSize = 20;  // Adjust how many messages you want per page

    public HL7Controller(HL7Service hl7Service, IWebHostEnvironment webHostEnvironment)
    {
        _hl7Service = hl7Service;
        _webHostEnvironment = webHostEnvironment;
    }

    public IActionResult Index(int page = 1)
    {
        int totalMessages = _messages.Count;
        var pagedMessages = _messages.Skip((page - 1) * PageSize).Take(PageSize).ToList();

        ViewBag.CurrentPage = page;
        ViewBag.TotalPages = (int)System.Math.Ceiling((double)totalMessages / PageSize);

        return View(pagedMessages);
    }

    public IActionResult LoadHL7File()
    {
        string filePath = Path.Combine(_webHostEnvironment.ContentRootPath, "Data", "source_hl7_messages_v2.hl7");

        if (System.IO.File.Exists(filePath))
        {
            _messages = HL7Service.ParseHL7File(filePath); 

        }

        return RedirectToAction("Index");
    }
    public ActionResult Details(string mrn, string facility)
    {
        string filePath = Path.Combine(_webHostEnvironment.ContentRootPath, "Data", "source_hl7_messages_v2.hl7");
        var messages = HL7Service.ParseHL7File(filePath);

        // Find all messages with the same MRN and Facility
        var matchingMessages = messages
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


}
