"""树节点图形项 — 在画布上显示电源树节点"""

from typing import Optional
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QLinearGradient, QFontMetrics
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsObject, QStyleOptionGraphicsItem, QWidget
)

from src.models.tree_node import TreeNode
from src.models.power_module import ModuleType


# ── 颜色方案 ─────────────────────────────────────────────

TYPE_COLORS = {
    "input_source": QColor("#2196F3"),   # 蓝色 - 输入
    "buck": QColor("#4CAF50"),           # 绿色 - 降压
    "boost": QColor("#FF9800"),          # 橙色 - 升压
    "buck_boost": QColor("#9C27B0"),     # 紫色 - 升降压
    "ldo": QColor("#00BCD4"),            # 青色 - LDO
    "load": QColor("#F44336"),           # 红色 - 负载
    "other": QColor("#607D8B"),          # 灰色 - 其他
}

TYPE_LIGHT_COLORS = {
    "input_source": QColor("#BBDEFB"),
    "buck": QColor("#C8E6C9"),
    "boost": QColor("#FFE0B2"),
    "buck_boost": QColor("#E1BEE7"),
    "ldo": QColor("#B2EBF2"),
    "load": QColor("#FFCDD2"),
    "other": QColor("#CFD8DC"),
}

NODE_WIDTH = 180
NODE_MIN_WIDTH = 160
NODE_HEIGHT = 110
CORNER_RADIUS = 10


class TreeNodeItem(QGraphicsObject):
    """画布上的电源树节点"""

    node_moved = Signal(str, float, float)     # node_id, x, y
    node_double_clicked = Signal(str)           # node_id

    def __init__(self, node: TreeNode, parent=None):
        super().__init__(parent)
        self._node = node
        self._width = NODE_MIN_WIDTH
        self._height = NODE_HEIGHT
        self._hovered = False
        self._dragging = False
        self._drag_start: Optional[QPointF] = None

        self.setPos(node.pos_x, node.pos_y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def _calc_width(self) -> float:
        """根据内容计算节点宽度"""
        font = QFont("Microsoft YaHei", 10)
        fm = QFontMetrics(font)
        # 芯片名 + 类型名
        chip = self._node.chip_name
        header_text = self._node.type_display
        if chip:
            header_text = f"{header_text}  {chip}"
        header_w = fm.horizontalAdvance(header_text) + 20

        name_w = fm.horizontalAdvance(self._node.name) + 20

        font_data = QFont("Consolas", 9)
        fm_data = QFontMetrics(font_data)
        vout_text = f"Vout: {self._node.output_voltage:.2f}V"
        vin_text = f"Vin: {self._node.input_voltage:.1f}V"
        data_w = fm_data.horizontalAdvance(vout_text) + \
                 fm_data.horizontalAdvance(vin_text) + 24

        return max(NODE_MIN_WIDTH, header_w, name_w, data_w)

    @property
    def node(self) -> TreeNode:
        return self._node

    @property
    def node_id(self) -> str:
        return self._node.id

    def boundingRect(self) -> QRectF:
        w = self._calc_width()
        return QRectF(-w / 2, -self._height / 2, w, self._height)

    # ── 鼠标事件 ──────────────────────────────────────

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.node_double_clicked.emit(self._node.id)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            new_pos = self.pos()
            self._node.pos_x = new_pos.x()
            self._node.pos_y = new_pos.y()
            self.node_moved.emit(self._node.id, new_pos.x(), new_pos.y())
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._dragging:
                self._node.pos_x = self.pos().x()
                self._node.pos_y = self.pos().y()
        return super().itemChange(change, value)

    # ── 绘制 ──────────────────────────────────────────

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 动态宽度
        self._width = self._calc_width()

        mtype = self._node.module_type
        primary = TYPE_COLORS.get(mtype, TYPE_COLORS["other"])
        light = TYPE_LIGHT_COLORS.get(mtype, TYPE_LIGHT_COLORS["other"])
        dark = primary.darker(120)
        rect = QRectF(-self._width / 2, -self._height / 2, self._width, self._height)

        # 阴影
        shadow_path = QPainterPath()
        shadow_rect = rect.translated(3, 3)
        shadow_path.addRoundedRect(shadow_rect, CORNER_RADIUS, CORNER_RADIUS)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 40))

        # 主体渐变
        body_path = QPainterPath()
        body_path.addRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, light.lighter(110))
        grad.setColorAt(1, light)
        painter.fillPath(body_path, grad)

        # 边框
        pen_width = 2.5 if self.isSelected() else 1.5
        if self._hovered:
            pen_width = 2.5
        border_pen = QPen(primary if self.isSelected() or self._hovered
                          else dark, pen_width)
        painter.setPen(border_pen)
        painter.drawPath(body_path)

        # 顶部色条 — 绘制只有上部圆角的矩形
        header_rect = QRectF(rect.left() + 1, rect.top() + 1,
                              rect.width() - 2, 28)
        header_path = QPainterPath()
        # 从左上角开始，画到右上角，再向下，再回来
        r = CORNER_RADIUS
        header_path.moveTo(header_rect.left() + r, header_rect.top())
        header_path.lineTo(header_rect.right() - r, header_rect.top())
        header_path.arcTo(QRectF(header_rect.right() - 2 * r, header_rect.top(),
                                  2 * r, 2 * r), 90, -90)
        header_path.lineTo(header_rect.right(), header_rect.bottom())
        header_path.lineTo(header_rect.left(), header_rect.bottom())
        header_path.lineTo(header_rect.left(), header_rect.top() + r)
        header_path.arcTo(QRectF(header_rect.left(), header_rect.top(),
                                  2 * r, 2 * r), 180, -90)
        header_path.closeSubpath()
        painter.fillPath(header_path, primary)

        # 类型标签 + 芯片名
        font_small = QFont("Microsoft YaHei", 9)
        font_small.setBold(True)
        painter.setFont(font_small)
        painter.setPen(QColor("white"))

        type_label = self._node.type_display or mtype
        chip = self._node.chip_name
        if chip:
            # 类型在左，芯片名在右（灰色小字）
            painter.drawText(QRectF(header_rect.left() + 6, header_rect.top(),
                                     header_rect.width() / 2, 28),
                             Qt.AlignmentFlag.AlignVCenter |
                             Qt.AlignmentFlag.AlignLeft, type_label)
            font_chip = QFont("Consolas", 9)
            font_chip.setBold(True)
            painter.setFont(font_chip)
            painter.setPen(QColor("#E0E0E0"))
            painter.drawText(QRectF(header_rect.left() + 6, header_rect.top(),
                                     header_rect.width() - 12, 28),
                             Qt.AlignmentFlag.AlignVCenter |
                             Qt.AlignmentFlag.AlignRight, chip)
        else:
            painter.drawText(QRectF(header_rect.left() + 6, header_rect.top(),
                                     header_rect.width() - 12, 28),
                             Qt.AlignmentFlag.AlignVCenter |
                             Qt.AlignmentFlag.AlignLeft, type_label)

        # 名称
        font_name = QFont("Microsoft YaHei", 10)
        font_name.setBold(True)
        painter.setFont(font_name)
        painter.setPen(QColor("#212121"))
        name = self._node.name if self._node.name else "未命名"
        fm = QFontMetrics(font_name)
        elided_name = fm.elidedText(name, Qt.TextElideMode.ElideRight,
                                     int(rect.width() - 16))
        painter.drawText(QRectF(rect.left() + 8, rect.top() + 32,
                                 rect.width() - 16, 22),
                         Qt.AlignmentFlag.AlignLeft, elided_name)

        # 电气参数
        font_data = QFont("Consolas", 9)
        painter.setFont(font_data)

        line_y = rect.top() + 56
        line_h = 15
        text_color = QColor("#424242")

        # 电压行
        painter.setPen(text_color)
        v_out = self._node.output_voltage
        v_in = self._node.input_voltage
        painter.drawText(QRectF(rect.left() + 8, line_y, rect.width() - 16, line_h),
                         Qt.AlignmentFlag.AlignLeft,
                         f"Vout: {v_out:.2f}V")
        painter.drawText(QRectF(rect.left() + 8, line_y, rect.width() - 16, line_h),
                         Qt.AlignmentFlag.AlignRight,
                         f"Vin: {v_in:.1f}V")

        # 功率行
        line_y += line_h
        eff_color = QColor("#2E7D32") if self._node.actual_efficiency >= 0.85 else (
            QColor("#FF6F00") if self._node.actual_efficiency >= 0.5 else QColor("#C62828")
        )
        painter.setPen(text_color)
        p_out = self._node.output_power
        painter.drawText(QRectF(rect.left() + 8, line_y, rect.width() - 16, line_h),
                         Qt.AlignmentFlag.AlignLeft,
                         f"Pout: {p_out:.2f}W")
        painter.setPen(eff_color)
        painter.drawText(QRectF(rect.left() + 8, line_y, rect.width() - 16, line_h),
                         Qt.AlignmentFlag.AlignRight,
                         f"η: {self._node.actual_efficiency * 100:.1f}%")

        # 损耗行
        line_y += line_h
        loss_color = QColor("#C62828") if self._node.power_loss > 1.0 else QColor("#795548")
        painter.setPen(loss_color)
        painter.drawText(QRectF(rect.left() + 8, line_y, rect.width() - 16, line_h),
                         Qt.AlignmentFlag.AlignLeft,
                         f"Ploss: {self._node.power_loss:.2f}W")

        # 连接点指示器（底部中心小圆）
        if not self._node.is_leaf or self._node.module_type != "load":
            conn_y = rect.bottom() - 5
            conn_path = QPainterPath()
            conn_path.addEllipse(QPointF(0, conn_y), 5, 5)
            painter.fillPath(conn_path, primary.darker(130))
            painter.setPen(QPen(primary, 1.5))
            painter.drawPath(conn_path)

        # 输入连接点（顶部中心小圆）
        if not self._node.is_root:
            conn_path2 = QPainterPath()
            conn_path2.addEllipse(QPointF(0, rect.top() + 5), 4, 4)
            painter.fillPath(conn_path2, QColor("#616161"))
            painter.setPen(QPen(QColor("#616161"), 1))
            painter.drawPath(conn_path2)

    # ── 连接点坐标 ────────────────────────────────────

    def output_point(self) -> QPointF:
        """底部输出连接点（场景坐标）"""
        return self.mapToScene(QPointF(0, self._height / 2))

    def input_point(self) -> QPointF:
        """顶部输入连接点（场景坐标）"""
        return self.mapToScene(QPointF(0, -self._height / 2))

    def scene_output_point(self) -> QPointF:
        """底部输出连接点"""
        return self.pos() + QPointF(0, self._height / 2)

    def scene_input_point(self) -> QPointF:
        """顶部输入连接点"""
        return self.pos() + QPointF(0, -self._height / 2)
