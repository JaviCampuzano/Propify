import math
import os
from datetime import datetime

from fpdf import FPDF


class ReceiptGenerator:
    MONTH_NAMES = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    COLORS = {
        "paper": (255, 250, 242),
        "paper_warm": (244, 239, 231),
        "ink": (29, 43, 54),
        "muted": (105, 115, 125),
        "line": (226, 216, 203),
        "accent": (196, 92, 47),
        "accent_strong": (138, 53, 17),
        "accent_soft": (242, 215, 199),
        "olive": (85, 107, 47),
        "white": (255, 255, 255),
        "mist": (247, 242, 235),
    }

    def _safe(self, text):
        return str(text).encode("latin-1", "replace").decode("latin-1")

    def _money(self, amount):
        return f"{amount:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")

    def _month_label(self, dt):
        return f"{self.MONTH_NAMES[dt.month].capitalize()} {dt.year}"

    def _status_label(self, status):
        labels = {
            "PAID": "Pagado",
            "PENDING": "Pendiente",
            "EMITTED": "Emitido",
        }
        return labels.get(str(status).upper(), "Emitido")

    def _set_fill(self, pdf, color_name):
        pdf.set_fill_color(*self.COLORS[color_name])

    def _set_text(self, pdf, color_name):
        pdf.set_text_color(*self.COLORS[color_name])

    def _set_draw(self, pdf, color_name):
        pdf.set_draw_color(*self.COLORS[color_name])

    def _rounded_rect(self, pdf, x, y, w, h, r, style=""):
        k = pdf.k
        hp = pdf.h
        op = {
            "F": "f",
            "FD": "B",
            "DF": "B",
        }.get(style, "S")
        my_arc = 4 / 3 * (math.sqrt(2) - 1)

        pdf._out(
            f"{(x + r) * k:.2f} {(hp - y) * k:.2f} m "
            f"{(x + w - r) * k:.2f} {(hp - y) * k:.2f} l"
        )
        self._arc(pdf, x + w - r + r * my_arc, y, x + w, y + r - r * my_arc, x + w, y + r)
        pdf._out(
            f"{(x + w) * k:.2f} {(hp - (y + h - r)) * k:.2f} l"
        )
        self._arc(pdf, x + w, y + h - r + r * my_arc, x + w - r + r * my_arc, y + h, x + w - r, y + h)
        pdf._out(
            f"{(x + r) * k:.2f} {(hp - (y + h)) * k:.2f} l"
        )
        self._arc(pdf, x + r - r * my_arc, y + h, x, y + h - r + r * my_arc, x, y + h - r)
        pdf._out(
            f"{x * k:.2f} {(hp - (y + r)) * k:.2f} l"
        )
        self._arc(pdf, x, y + r - r * my_arc, x + r - r * my_arc, y, x + r, y)
        pdf._out(op)

    def _arc(self, pdf, x1, y1, x2, y2, x3, y3):
        h = pdf.h
        k = pdf.k
        pdf._out(
            f"{x1 * k:.2f} {(h - y1) * k:.2f} "
            f"{x2 * k:.2f} {(h - y2) * k:.2f} "
            f"{x3 * k:.2f} {(h - y3) * k:.2f} c"
        )

    def generate_receipt(self, tenant, property_obj):
        today = datetime.now()
        month_key = today.strftime("%Y-%m")
        receipt_ref = f"{property_obj.id[:4].upper()}-{tenant.id[:4].upper()}-{today.strftime('%Y%m')}"
        period_label = self._month_label(today)
        property_location = ", ".join(filter(None, [property_obj.city, property_obj.zip_code, property_obj.country])) or "Espana"
        status_label = self._status_label(getattr(tenant, "payments", {}).get(month_key, "EMITTED"))

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        self._set_fill(pdf, "paper")
        pdf.rect(0, 0, 210, 297, "F")

        self._set_fill(pdf, "paper_warm")
        pdf.rect(0, 0, 58, 297, "F")
        self._set_fill(pdf, "accent_soft")
        pdf.ellipse(118, -24, 96, 96, "F")
        self._set_fill(pdf, "mist")
        pdf.ellipse(130, 208, 86, 86, "F")
        self._set_fill(pdf, "ink")
        pdf.rect(16, 20, 10, 68, "F")
        self._set_fill(pdf, "accent")
        pdf.rect(16, 88, 10, 18, "F")
        self._set_draw(pdf, "accent_soft")
        pdf.line(70, 78, 194, 78)

        self._set_text(pdf, "ink")
        pdf.set_xy(32, 22)
        pdf.set_font("Times", "B", 29)
        pdf.cell(130, 10, self._safe("Recibo"))
        pdf.set_xy(32, 34)
        pdf.cell(130, 10, self._safe("de alquiler"))

        self._set_text(pdf, "muted")
        pdf.set_xy(32, 49)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(78, 5.3, self._safe("Pieza mensual emitida con la misma linea visual de la aplicacion web."))
        self._status_badge(pdf, 32, 64, status_label)

        self._set_text(pdf, "ink")
        pdf.set_xy(154, 26)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(34, 5, self._safe("Referencia"), align="R")
        self._set_text(pdf, "accent_strong")
        pdf.set_xy(154, 32)
        pdf.set_font("Arial", "", 10)
        pdf.cell(34, 5, receipt_ref, align="R")
        self._set_text(pdf, "ink")
        pdf.set_xy(154, 42)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(34, 5, self._safe("Fecha"), align="R")
        self._set_text(pdf, "muted")
        pdf.set_xy(154, 48)
        pdf.set_font("Arial", "", 10)
        pdf.cell(34, 5, today.strftime("%d/%m/%Y"), align="R")

        self._sidebar_label(pdf, 18, 122, "Periodo", period_label)
        self._sidebar_label(pdf, 18, 163, "Estado", status_label)
        self._sidebar_label(pdf, 18, 204, "Importe", self._money(tenant.rent))

        self._hero_amount(pdf, 70, 86, tenant.rent, period_label, receipt_ref)
        self._party_card(
            pdf,
            70,
            132,
            62,
            64,
            "Inquilino",
            [
                tenant.name,
                f"Inicio contrato: {tenant.start_date}",
                f"Renta mensual: {self._money(tenant.rent)}",
            ],
        )
        self._party_card(
            pdf,
            138,
            132,
            56,
            64,
            "Propiedad",
            [
                property_obj.address,
                property_location,
                f"Periodo liquidado: {period_label.lower()}",
            ],
        )

        self._detail_panel(pdf, 70, 205, 124, 50, period_label, tenant.rent, status_label, property_obj.address)
        self._notes_block(pdf, 70, 261, 124, 24, tenant.name)

        self._set_draw(pdf, "line")
        pdf.line(16, 286, 194, 286)
        self._set_text(pdf, "muted")
        pdf.set_xy(16, 289)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(178, 4, self._safe("Gestor de Recibos de Alquiler · composicion editorial coordinada con la interfaz web"), align="C")

        filename = f"Recibo_{tenant.name.replace(' ', '_')}_{today.strftime('%Y%m')}.pdf"
        pdf.output(filename)
        return os.path.abspath(filename)

    def _sidebar_label(self, pdf, x, y, title, value):
        self._set_text(pdf, "muted")
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(34, 4, self._safe(title.upper()))
        self._set_text(pdf, "ink")
        pdf.set_xy(x, y + 8)
        pdf.set_font("Times", "B", 16 if title == "Importe" else 12)
        pdf.multi_cell(30, 6, self._safe(value))

    def _status_badge(self, pdf, x, y, status_label):
        self._set_fill(pdf, "accent_soft" if status_label != "Pagado" else "olive")
        self._rounded_rect(pdf, x, y, 30, 10, 3, "F")
        self._set_text(pdf, "accent_strong" if status_label != "Pagado" else "white")
        pdf.set_xy(x, y + 3)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(30, 4, self._safe(status_label.upper()), align="C")

    def _hero_amount(self, pdf, x, y, amount, period_label, receipt_ref):
        self._set_fill(pdf, "ink")
        self._rounded_rect(pdf, x, y, 124, 38, 6, "F")
        self._set_fill(pdf, "accent")
        self._rounded_rect(pdf, x + 86, y + 6, 28, 10, 3, "F")
        self._set_text(pdf, "paper")
        pdf.set_xy(x + 8, y + 6)
        pdf.set_font("Arial", "", 10)
        pdf.cell(40, 5, self._safe("Total del recibo"))
        pdf.set_xy(x + 8, y + 13)
        pdf.set_font("Times", "B", 24)
        pdf.cell(86, 10, self._money(amount))
        self._set_text(pdf, "white")
        pdf.set_xy(x + 86, y + 9)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(28, 4, self._safe(period_label[:3].upper()), align="C")
        self._set_text(pdf, "paper_warm")
        pdf.set_xy(x + 8, y + 28)
        pdf.set_font("Arial", "", 8.5)
        pdf.cell(60, 4, self._safe(f"Referencia {receipt_ref}"))
        pdf.set_xy(x + 70, y + 28)
        pdf.cell(46, 4, self._safe("Cuota ordinaria de arrendamiento"), align="R")

    def _party_card(self, pdf, x, y, w, h, title, lines):
        self._set_fill(pdf, "white")
        self._set_draw(pdf, "line")
        self._rounded_rect(pdf, x, y, w, h, 5, "FD")
        self._set_fill(pdf, "accent_soft")
        self._rounded_rect(pdf, x + 4, y + 4, w - 8, 10, 3, "F")
        self._set_text(pdf, "accent_strong")
        pdf.set_xy(x + 8, y + 7)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(w - 16, 4, self._safe(title.upper()))
        self._set_text(pdf, "ink")
        current_y = y + 21
        for index, line in enumerate(lines):
            pdf.set_xy(x + 8, current_y)
            pdf.set_font("Arial", "B" if index == 0 else "", 10 if index == 0 else 9)
            pdf.multi_cell(w - 16, 5.2, self._safe(line))
            current_y += 10 if index == 0 else 8

    def _detail_panel(self, pdf, x, y, w, h, period_label, amount, status_label, address):
        self._set_fill(pdf, "white")
        self._set_draw(pdf, "line")
        self._rounded_rect(pdf, x, y, w, h, 5, "FD")
        self._set_text(pdf, "ink")
        pdf.set_xy(x + 8, y + 8)
        pdf.set_font("Times", "B", 18)
        pdf.cell(60, 7, self._safe("Detalle"))
        self._set_text(pdf, "muted")
        pdf.set_xy(x + 8, y + 17)
        pdf.set_font("Arial", "", 9)
        pdf.cell(70, 4, self._safe("Desglose del recibo mensual"))

        self._mini_stat(pdf, x + 8, y + 28, 36, 14, "Concepto", "Renta")
        self._mini_stat(pdf, x + 48, y + 28, 32, 14, "Periodo", period_label.split()[0][:3].upper())
        self._mini_stat(pdf, x + 84, y + 28, 32, 14, "Estado", status_label)

        self._set_text(pdf, "ink")
        pdf.set_xy(x + 10, y + 46)
        pdf.set_font("Arial", "B", 10.5)
        pdf.cell(70, 5, self._safe("Renta mensual de vivienda"))
        pdf.set_xy(x + 10, y + 51)
        pdf.set_font("Arial", "", 8.5)
        pdf.multi_cell(68, 4.2, self._safe(f"Correspondiente a {period_label.lower()} para la vivienda situada en {address}."))
        pdf.set_xy(x + 108, y + 47)
        pdf.set_font("Times", "B", 17)
        pdf.cell(0, 8, self._money(amount), align="R")

    def _mini_stat(self, pdf, x, y, w, h, label, value):
        self._set_fill(pdf, "paper_warm")
        self._rounded_rect(pdf, x, y, w, h, 2.5, "F")
        self._set_text(pdf, "muted")
        pdf.set_xy(x, y + 2.8)
        pdf.set_font("Arial", "B", 6.8)
        pdf.cell(w, 3, self._safe(label.upper()), align="C")
        self._set_text(pdf, "ink")
        pdf.set_xy(x + 2, y + 7.4)
        pdf.set_font("Arial", "B", 8.5)
        pdf.cell(w - 4, 4, self._safe(value), align="C")

    def _notes_block(self, pdf, x, y, w, h, tenant_name):
        self._set_fill(pdf, "paper_warm")
        self._rounded_rect(pdf, x, y, w, h, 4, "F")
        self._set_text(pdf, "muted")
        pdf.set_xy(x + 8, y + 4)
        pdf.set_font("Arial", "", 8.5)
        note = (
            "Este documento acredita la emision del recibo. "
            "Conservalo junto con el justificante bancario del pago."
        )
        pdf.multi_cell(76, 4.4, self._safe(note))
        self._set_draw(pdf, "line")
        pdf.line(x + 88, y + 15, x + w - 8, y + 15)
        self._set_text(pdf, "ink")
        pdf.set_xy(x + 88, y + 16)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(w - 96, 4, self._safe("Recibido por"))
        self._set_text(pdf, "muted")
        pdf.set_xy(x + 88, y + 20)
        pdf.set_font("Arial", "", 8)
        pdf.cell(w - 96, 4, self._safe(tenant_name[:28]))
