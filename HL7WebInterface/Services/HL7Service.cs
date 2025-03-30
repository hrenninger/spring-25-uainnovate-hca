using HL7WebInterface.Models;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

public class HL7Service
{
    private static int messageIdCounter = 1;
    private static Dictionary<int, string> redactedMessages = new Dictionary<int, string>();

    public static List<HL7Message> ParseHL7File(string filePath)
    {
        List<HL7Message> messages = new List<HL7Message>();

        if (!File.Exists(filePath)) return messages;

        string[] lines = File.ReadAllLines(filePath);
        HL7Message currentMessage = null;
        List<HL7Segment> segments = new List<HL7Segment>();
        int segmentSequence = 0;

        foreach (string line in lines)
        {
            string[] fields = line.Split('|');

            if (fields.Length == 0) continue; // Ignore empty lines

            string segmentType = fields[0];

            if (segmentType == "MSH")  // New HL7 message starts here
            {
                if (currentMessage != null)
                {
                    currentMessage.Segments = new List<HL7Segment>(segments);
                    messages.Add(currentMessage);
                }

                segmentSequence = 0; // Reset for new message
                segments = new List<HL7Segment>(); // Reset segments list

                // Parse HL7 message timestamp (MSH-7)
                string msh7 = fields.Length > 6 ? fields[6] : "";
                DateTime parsedDateTime = ParseHL7DateTime(msh7);

                currentMessage = new HL7Message
                {
                    Id = messageIdCounter++,
                    RawMessage = "", // Start with an empty string
                    DateTime = parsedDateTime,
                    MSH7 = msh7,
                    MSH9 = fields.Length > 8 ? fields[8] : "",
                    MSH10 = fields.Length > 9 ? fields[9] : "",
                    Facility = fields.Length > 3 ? fields[3] : "",
                    Segments = new List<HL7Segment>()
                };
            }

            if (currentMessage != null)
            {
                currentMessage.RawMessage += line + "\n"; // Append each segment to the raw message
            }

            if (currentMessage != null)
            {
                // Create a new segment
                HL7Segment segment = new HL7Segment
                {
                    HL7Message = currentMessage,
                    SegmentType = segmentType,
                    Sequence = segmentSequence++,
                    Fields = new List<HL7Field>()
                };

                // Parse fields within segment
                for (int i = 1; i < fields.Length; i++)
                {
                    segment.Fields.Add(new HL7Field
                    {
                        HL7Segment = segment,
                        FieldLabel = $"{segmentType}-{i}",
                        Value = fields[i],
                        FieldPosition = i
                    });

                    // Extract key fields for HL7Message
                    if (segmentType == "PID")
                    {
                        if (i == 3) currentMessage.MRN = fields[i];  // PID-3: MRN
                        if (i == 5) currentMessage.LastName = fields[i].Split('^').FirstOrDefault(); // PID-5: Last Name
                        if (i == 5) currentMessage.FirstName = fields[i].Split('^').Skip(1).FirstOrDefault(); // PID-5: First Name
                        if (i == 18) currentMessage.AccountNumber = fields[i]; // PID-18: Account Number
                    }
                }

                segments.Add(segment);
            }
        }

        // Add the last message
        if (currentMessage != null)
        {
            currentMessage.Segments = new List<HL7Segment>(segments);
            messages.Add(currentMessage);
        }

        return messages;
    }

    public static void LoadRedactedMessages(string filePath)
    {
        if (!File.Exists(filePath)) return;

        string[] lines = File.ReadAllLines(filePath);
        int currentId = 0;
        StringBuilder messageBuilder = new StringBuilder();

        foreach (string line in lines)
        {
            string[] fields = line.Split('|');

            if (fields.Length == 0) continue; // Ignore empty lines

            string segmentType = fields[0];

            if (segmentType == "MSH")  // New HL7 message starts here
            {
                // Save the previous message if there was one
                if (messageBuilder.Length > 0 && currentId > 0)
                {
                    redactedMessages[currentId] = messageBuilder.ToString();
                    messageBuilder.Clear();
                }

                // Start a new message
                currentId++;
            }

            // Append the current line to the message
            messageBuilder.AppendLine(line);
        }

        // Save the last message
        if (messageBuilder.Length > 0 && currentId > 0)
        {
            redactedMessages[currentId] = messageBuilder.ToString();
        }
    }

    public static string GetRedactedMessage(int id)
    {
        if (redactedMessages.TryGetValue(id, out string message))
        {
            return message;
        }
        return "Redacted message not found";
    }

    private static DateTime ParseHL7DateTime(string hl7DateTime)
    {
        if (string.IsNullOrWhiteSpace(hl7DateTime)) return DateTime.Now;

        // Remove all non-numeric characters
        string cleanedDateTime = new string(hl7DateTime.Where(char.IsDigit).ToArray());

        // Trim to appropriate length
        if (cleanedDateTime.Length >= 14) cleanedDateTime = cleanedDateTime.Substring(0, 14);
        else if (cleanedDateTime.Length >= 12) cleanedDateTime = cleanedDateTime.Substring(0, 12);
        else if (cleanedDateTime.Length >= 8) cleanedDateTime = cleanedDateTime.Substring(0, 8);

        if (DateTime.TryParseExact(
            cleanedDateTime,
            new[] { "yyyyMMddHHmmss", "yyyyMMddHHmm", "yyyyMMdd" },
            CultureInfo.InvariantCulture,
            DateTimeStyles.None,
            out DateTime parsedDate))
        {
            return parsedDate;
        }

        return DateTime.Now;
    }
}