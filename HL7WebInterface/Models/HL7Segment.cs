namespace HL7WebInterface.Models
{
    public class HL7Segment
    {
        public int Id { get; set; }
        public int HL7MessageId { get; set; }
        public string SegmentType { get; set; }  // e.g., "MSH", "PID", "PV1"
        public int Sequence { get; set; }  // Order within the message

        // Relationship to Message
        public HL7Message HL7Message { get; set; }

        // Relationship to Fields
        public List<HL7Field> Fields { get; set; } = new List<HL7Field>();
    }
}
