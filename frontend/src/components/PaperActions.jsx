/**
 * Reusable action button for adding/removing papers from Papers of Interest
 */
export default function PaperActions({ doi, isInList, onToggle }) {
  return (
    <button
      onClick={() => onToggle(doi)}
      style={{
        padding: "6px 12px",
        background: isInList ? "#dc3545" : "#228B22",
        color: "#fff",
        border: "none",
        borderRadius: "4px",
        cursor: "pointer",
        fontSize: "0.85rem",
        fontWeight: 600,
        transition: "all 0.2s ease",
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
      }}
      onMouseEnter={(e) => {
        e.target.style.opacity = "0.85";
        e.target.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        e.target.style.opacity = "1";
        e.target.style.transform = "translateY(0)";
      }}
    >
      {isInList ? (
        <>
          <span>−</span> Remove from List
        </>
      ) : (
        <>
          <span>+</span> Add to List
        </>
      )}
    </button>
  );
}


