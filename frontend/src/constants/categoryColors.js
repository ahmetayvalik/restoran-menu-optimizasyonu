export const CATEGORY_COLORS = {
  Asian: "#8B5CF6",
  Italian: "#EF4444",
  Mexican: "#F97316",
  American: "#3B82F6",
  Mixed: "#6B7280",
  null: "#6B7280"
};

export function getCategoryColor(category) {
  if (!category) {
    return CATEGORY_COLORS.null;
  }

  return CATEGORY_COLORS[category] || CATEGORY_COLORS.Mixed;
}
