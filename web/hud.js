export const COLORS = {
  green: "#53ff78",
  dim: "#176d31",
  amber: "#ffc24b",
  red: "#ff5151",
};

export function drawGrid(ctx, width, height, spacing = 64) {
  ctx.save();
  ctx.strokeStyle = COLORS.dim;
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += spacing) line(ctx, x, 0, x, height);
  for (let y = 0; y < height; y += spacing) line(ctx, 0, y, width, y);
  ctx.restore();
}

export function drawCrosshair(ctx, center, size = 40) {
  ctx.save();
  ctx.strokeStyle = COLORS.green;
  ctx.fillStyle = COLORS.green;
  ctx.lineWidth = 2;
  line(ctx, center.x - size, center.y, center.x - 8, center.y);
  line(ctx, center.x + 8, center.y, center.x + size, center.y);
  line(ctx, center.x, center.y - size, center.x, center.y - 8);
  line(ctx, center.x, center.y + 8, center.x, center.y + size);
  ctx.beginPath();
  ctx.arc(center.x, center.y, size, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(center.x, center.y, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

export function drawLockBrackets(ctx, box, label) {
  const arm = Math.max(10, Math.min(box.width, box.height) / 4);
  ctx.save();
  ctx.strokeStyle = COLORS.green;
  ctx.fillStyle = COLORS.green;
  ctx.lineWidth = 2;
  for (const [x, y, dx, dy] of [
    [box.x, box.y, 1, 1], [box.x + box.width, box.y, -1, 1],
    [box.x, box.y + box.height, 1, -1], [box.x + box.width, box.y + box.height, -1, -1],
  ]) {
    line(ctx, x, y, x + dx * arm, y);
    line(ctx, x, y, x, y + dy * arm);
  }
  ctx.font = "16px 'Courier New', monospace";
  ctx.fillText(label, box.x, Math.max(18, box.y - 10));
  ctx.restore();
}

export function drawText(ctx, lines, { x = 22, y = 32, color = COLORS.green, size = 18, gap = 27 } = {}) {
  ctx.save();
  ctx.fillStyle = color;
  ctx.font = `${size}px 'Courier New', monospace`;
  lines.forEach((text, index) => ctx.fillText(text, x, y + index * gap));
  ctx.restore();
}

export function drawMeter(ctx, { x, y, width, height, value, max = 100, label, color = COLORS.green }) {
  const fraction = Math.max(0, Math.min(1, value / max));
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1;
  ctx.strokeRect(x, y, width, height);
  ctx.fillRect(x, y, width * fraction, height);
  ctx.font = "14px 'Courier New', monospace";
  if (label) ctx.fillText(label, x, y - 8);
  ctx.restore();
}

export function drawBanner(ctx, width, height, text, color = COLORS.green) {
  ctx.save();
  ctx.fillStyle = "rgba(0, 8, 2, .68)";
  ctx.fillRect(0, height - 48, width, 48);
  ctx.fillStyle = color;
  ctx.font = "bold 19px 'Courier New', monospace";
  ctx.textAlign = "center";
  ctx.fillText(text, width / 2, height - 18);
  ctx.restore();
}

function line(ctx, x1, y1, x2, y2) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}
