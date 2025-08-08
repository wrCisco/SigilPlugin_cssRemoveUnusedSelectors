from plugin_utils import QtWidgets, Qt, QtCore


class WrappingCheckBox(QtWidgets.QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 2)
        self.layout.setSpacing(5)
        
        self.checkbox = QtWidgets.QCheckBox()
        
        self.label = QtWidgets.QLabel(text)
        self.label.setWordWrap(True)
        
        # Make label clickable to toggle checkbox
        self.label.mousePressEvent = self._on_label_click
        
        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.label, 1)  # Label takes remaining space
        self.layout.setAlignment(self.checkbox, Qt.AlignCenter)
        self.layout.setAlignment(self.label, Qt.AlignLeft|Qt.AlignVCenter)
    
    def resizeEvent(self, event):
        """Handle resize events to update text wrapping"""
        super().resizeEvent(event)
        self._updateLabelWidth()

    def showEvent(self, event):
        """Handle show events to ensure proper initial sizing"""
        super().showEvent(event)
        self._updateLabelWidth()

    def _updateLabelWidth(self):
        """Calculate and set the appropriate width for the label"""
        if self.width() <= 1:  # Skip if not properly sized yet
            return
        # Calculate available width for the label
        margins = self.layout.contentsMargins()
        spacing = self.layout.spacing()
        available_width = (
            self.width() - self.checkbox.width() - spacing -
            margins.left() - margins.right()
        )
        available_width = max(available_width, 50)  # Ensure minimum width
        # I'm not sure why if I use exactly available_width
        # as argument for setFixedWidth, the label grows but
        # does not shrink as needed.
        self.label.setFixedWidth(available_width - 1)
        self.label.updateGeometry()
        self.updateGeometry()

    def _on_label_click(self, event):
        """Handle label click to toggle checkbox"""
        self.checkbox.toggle()
    
    def setText(self, text):
        """Set the text displayed in the label"""
        self.label.setText(text)
    
    def text(self):
        """Get the text from the label"""
        return self.label.text()
    
    def setChecked(self, checked):
        """Set checkbox checked state"""
        self.checkbox.setChecked(checked)
    
    def isChecked(self):
        """Get checkbox checked state"""
        return self.checkbox.isChecked()
    
    def toggle(self):
        """Toggle checkbox state"""
        self.checkbox.toggle()
    
    def setEnabled(self, enabled):
        """Enable/disable the widget"""
        super().setEnabled(enabled)
        self.checkbox.setEnabled(enabled)
        self.label.setEnabled(enabled)
    
    def checkStateChanged(self):
        """Access to the checkbox's checkStateChanged signal"""
        return self.checkbox.checkStateChanged
    
    def stateChanged(self):
        """Access to the checkbox's stateChanged signal (for older Qt compatibility)"""
        return self.checkbox.stateChanged if hasattr(self.checkbox, 'stateChanged') else self.checkbox.checkStateChanged
    
    def clicked(self):
        """Access to the checkbox's clicked signal"""
        return self.checkbox.clicked
    
    def toggled(self):
        """Access to the checkbox's toggled signal"""
        return self.checkbox.toggled
