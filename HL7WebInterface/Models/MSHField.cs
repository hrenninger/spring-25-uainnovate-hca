using System.ComponentModel.DataAnnotations.Schema;

namespace HL7WebInterface.Models
{
    public class MSHField
    {
        public int Id { get; set; }

        [ForeignKey("MSHSegmentId")]
        public int MSHSegmentId { get; set; }
        public int FieldNumber { get; set; }
        public string Value { get; set; }
    }
}
