namespace HL7WebInterface.Models
{
    public class HL7Field
    {
        public int Id { get; set; }
        public int HL7SegmentId { get; set; }
        public string FieldLabel { get; set; }  // e.g., "PID-3", "MSH-7"
        public string Value { get; set; }  // Extracted field value
        public int FieldPosition { get; set; }  // Field order within the segment

        // Relationship to Segment
        public HL7Segment HL7Segment { get; set; }
    }
}
