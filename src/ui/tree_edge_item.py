"""树连线图形项 — 绘制父子节点间的贝塞尔曲线，支持点击删除"""

from typing import Optional
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import (
    QPainter, QPen, QColor, QPainterPath, QPolygonF, QFont
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget
)


class TreeEdgeItem(QObject, QGraphicsPathItem):
    """父子节点间的连线，可点击（继承 QObject + QGraphicsPathItem 以支持 Signal）"""

    edge_clicked = Signal(tuple)  # (parent_id, child_id)

    def __init__(self, parent_id: str = "", child_id: str = "",
                 parent_item: Optional[QGraphicsItem] = None):
        QObject.__init__(self)
        QGraphicsPathItem.__init__(self, parent_item)
        self._source_point = QPointF(0, 0)
        self._target_point = QPointF(0, 100)
        self._power_flow: float = 0.0
        self._current_flow: float = 0.0
        self._parent_id = parent_id
        self._child_id = child_id
        self._hovered = False

        self.setPen(QPen(QColor("#90A4AE"), 2.5, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap,
                         Qt.PenJoinStyle.RoundJoin))
        self.setZValue(5)
        self.setAcceptHoverEvents(True)
        # 设置一个宽的可点击区域
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def set_ids(self, parent_id: str, child_id: str) -> None:
        self._parent_id = parent_id
        self._child_id = child_id

    def set_points(self, source: QPointF, target: QPointF) -> None:
        self._source_point = source
        self._target_point = target
        self._update_path()

    def set_flows(self, power: float, current: float) -> None:
        self._power_flow = power
        self._current_flow = current

    def _update_path(self) -> None:
        """生成 90° 正交连线路径"""
        path = QPainterPath()
        sx, sy = self._source_point.x(), self._source_point.y()
        tx, ty = self._target_point.x(), self._target_point.y()

        path.moveTo(sx, sy)

        # 直角走线：先竖后横再竖
        mid_y = (sy + ty) / 2

        if abs(sx - tx) < 5:
            # 几乎垂直对齐：直接画直线
            path.lineTo(tx, ty)
        else:
            # 正交路径: 下 → 横 → 下
            path.lineTo(sx, mid_y)
            path.lineTo(tx, mid_y)
            path.lineTo(tx, ty)

        self.setPath(path)

    def shape(self) -> QPainterPath:
        """扩大碰撞检测区域（让细线更容易点击）"""
        stroker = QPainterPath()
        pen = QPen()
        pen.setWidthF(12)  # 12px 宽的点击区域
        stroker.addPath(self.path())
        return stroker

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-8, -8, 8, 8)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setPen(QPen(QColor("#F44336"), 3.5, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap,
                         Qt.PenJoinStyle.RoundJoin))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setPen(QPen(QColor("#90A4AE"), 2.5, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap,
                         Qt.PenJoinStyle.RoundJoin))
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.edge_clicked.emit((self._parent_id, self._child_id))
            event.accept()
        else:
            super().mousePressEvent(event)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = self.pen()
        if self._hovered:
            pen = QPen(QColor("#F44336"), 3.5, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # 箭头
        if self.path().elementCount() > 0:
            end_pt = self.path().currentPosition()
            percent = 0.98
            pt = self.path().pointAtPercent(percent)
            pt2 = self.path().pointAtPercent(min(percent + 0.01, 1.0))
            dx = pt2.x() - pt.x()
            dy = pt2.y() - pt.y()
            length = (dx ** 2 + dy ** 2) ** 0.5
            if length > 0.01:
                dx /= length
                dy /= length
                arrow_size = 10
                arrow = QPolygonF([
                    QPointF(end_pt.x(), end_pt.y()),
                    QPointF(end_pt.x() - arrow_size * dx + arrow_size * 0.4 * dy,
                            end_pt.y() - arrow_size * dy - arrow_size * 0.4 * dx),
                    QPointF(end_pt.x() - arrow_size * dx - arrow_size * 0.4 * dy,
                            end_pt.y() - arrow_size * dy + arrow_size * 0.4 * dx),
                ])
                arrow_color = QColor("#F44336") if self._hovered else QColor("#78909C")
                painter.setBrush(arrow_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(arrow)

        # 功率标签
        mid_pt = self.path().pointAtPercent(0.5)
        painter.setPen(QColor("#546E7A"))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        if self._power_flow > 0:
            label = f"{self._power_flow:.1f}W / {self._current_flow:.2f}A"
            # 半透明背景
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label) + 6
            th = fm.height() + 2
            bg_rect = QRectF(mid_pt.x() - tw / 2, mid_pt.y() - th + 2, tw, th)
            painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, label)

        # hover 时显示删除提示
        if self._hovered:
            mid_pt2 = self.path().pointAtPercent(0.4)
            painter.setPen(QColor("#D32F2F"))
            font2 = QFont()
            font2.setPointSize(9)
            font2.setBold(True)
            painter.setFont(font2)
            painter.drawText(mid_pt2 + QPointF(-20, -12), "点击删除连接")
