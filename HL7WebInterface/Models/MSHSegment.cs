using System.ComponentModel.DataAnnotations.Schema;

namespace HL7WebInterface.Models
{
    public class MSHSegment
    {
        public int Id { get; set; }

        [ForeignKey("HL7MessageId")]
        public int HL7MessageId { get; set; }

        public HL7Message HL7Message { get; set; }

        public List<MSHField> MSHFields { get; set; }
    }
}
