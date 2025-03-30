namespace HL7WebInterface.Models
{
    public class HL7Message
    {
        public int Id { get; set; }
        public string RawMessage { get; set; }  // Full HL7 message
        public DateTime DateTime { get; set; }

        // Parsed Key Fields for Table View
        public string MRN { get; set; }  // PID-3
        public string Facility { get; set; }  // MSH-4
        public string AccountNumber { get; set; }  // PID-18
        public string LastName { get; set; }  // PID-5
        public string FirstName { get; set; }  // PID-5
        public string MSH7 { get; set; }  // Message Date/Time
        public string MSH9 { get; set; }  // Message Type
        public string MSH10 { get; set; }  // Message Control ID

        // Relationship to Segments
        public List<HL7Segment> Segments { get; set; } = new List<HL7Segment>();
    }
}
