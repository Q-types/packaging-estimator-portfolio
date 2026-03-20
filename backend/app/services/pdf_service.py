"""PDF quote generation service using ReportLab."""

import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# Brand colors
PackagePro_DARK = colors.HexColor("#1a2332")
PackagePro_BLUE = colors.HexColor("#2563eb")
PackagePro_LIGHT_BLUE = colors.HexColor("#dbeafe")
PackagePro_GREY = colors.HexColor("#6b7280")
PackagePro_LIGHT_GREY = colors.HexColor("#f3f4f6")
PackagePro_GREEN = colors.HexColor("#059669")


class QuotePDFGenerator:
    """Generate professional PDF quotes for packaging estimates."""

    def __init__(
        self,
        company_name: str = "PackagePro Ltd",
        company_address: str = "Unit 5, Industrial Estate\nBirmingham, B12 0HG",
        company_phone: str = "+44 (0)121 xxx xxxx",
        company_email: str = "sales@ksppackaging.co.uk",
    ):
        self.company_name = company_name
        self.company_address = company_address
        self.company_phone = company_phone
        self.company_email = company_email
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Set up custom paragraph styles."""
        self.styles = getSampleStyleSheet()

        self.styles.add(ParagraphStyle(
            "CompanyName",
            parent=self.styles["Heading1"],
            fontSize=20,
            textColor=PackagePro_DARK,
            spaceAfter=2 * mm,
        ))
        self.styles.add(ParagraphStyle(
            "QuoteTitle",
            parent=self.styles["Heading1"],
            fontSize=16,
            textColor=PackagePro_BLUE,
            alignment=TA_CENTER,
            spaceBefore=6 * mm,
            spaceAfter=6 * mm,
        ))
        self.styles.add(ParagraphStyle(
            "SectionHeader",
            parent=self.styles["Heading2"],
            fontSize=11,
            textColor=PackagePro_DARK,
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
        ))
        self.styles.add(ParagraphStyle(
            "DetailText",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=PackagePro_GREY,
            leading=13,
        ))
        self.styles.add(ParagraphStyle(
            "FooterText",
            parent=self.styles["Normal"],
            fontSize=7,
            textColor=PackagePro_GREY,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            "TotalLabel",
            parent=self.styles["Normal"],
            fontSize=12,
            textColor=PackagePro_DARK,
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            "TotalValue",
            parent=self.styles["Normal"],
            fontSize=14,
            textColor=PackagePro_BLUE,
            alignment=TA_RIGHT,
        ))

    def generate(
        self,
        reference_number: str,
        job_name: str,
        customer_name: Optional[str],
        customer_contact: Optional[str],
        customer_address: Optional[str],
        quantity: int,
        dimensions: dict[str, Any],
        materials: dict[str, Any],
        operations: list[str],
        cost_breakdown: dict[str, Any],
        total_cost: Decimal,
        unit_cost: Optional[Decimal],
        quoted_price: Optional[Decimal],
        confidence_level: Optional[float],
        notes: Optional[str] = None,
        validity_days: int = 30,
    ) -> bytes:
        """
        Generate a PDF quote.

        Returns PDF content as bytes.
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=15 * mm,
            bottomMargin=20 * mm,
        )

        elements = []

        # Header
        elements.extend(self._build_header(reference_number))

        # Customer details
        elements.extend(self._build_customer_section(
            customer_name, customer_contact, customer_address
        ))

        # Job details
        elements.extend(self._build_job_section(
            job_name, quantity, dimensions, materials, operations
        ))

        # Cost breakdown
        elements.extend(self._build_cost_section(cost_breakdown))

        # Totals
        elements.extend(self._build_totals_section(
            total_cost, unit_cost, quoted_price, quantity, confidence_level
        ))

        # Notes
        if notes:
            elements.append(Paragraph("Notes", self.styles["SectionHeader"]))
            elements.append(Paragraph(notes, self.styles["DetailText"]))

        # Terms
        elements.extend(self._build_terms_section(validity_days))

        # Footer
        elements.extend(self._build_footer())

        doc.build(elements)
        return buffer.getvalue()

    def _build_header(self, reference_number: str) -> list:
        """Build the quote header with company info and reference."""
        elements = []

        # Company name and quote info side by side
        header_data = [
            [
                Paragraph(self.company_name, self.styles["CompanyName"]),
                Paragraph(
                    f"<b>QUOTATION</b><br/>"
                    f"Ref: {reference_number}<br/>"
                    f"Date: {datetime.now().strftime('%d %B %Y')}",
                    self.styles["DetailText"],
                ),
            ],
            [
                Paragraph(
                    self.company_address.replace("\n", "<br/>"),
                    self.styles["DetailText"],
                ),
                "",
            ],
            [
                Paragraph(
                    f"Tel: {self.company_phone}<br/>Email: {self.company_email}",
                    self.styles["DetailText"],
                ),
                "",
            ],
        ]

        header_table = Table(
            header_data,
            colWidths=[110 * mm, 60 * mm],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LINEBELOW", (0, -1), (-1, -1), 1, PackagePro_BLUE),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 4 * mm))
        return elements

    def _build_customer_section(
        self,
        name: Optional[str],
        contact: Optional[str],
        address: Optional[str],
    ) -> list:
        """Build the customer details section."""
        elements = []
        elements.append(Paragraph("Customer", self.styles["SectionHeader"]))

        customer_parts = []
        if name:
            customer_parts.append(f"<b>{name}</b>")
        if contact:
            customer_parts.append(f"Attn: {contact}")
        if address:
            customer_parts.append(address.replace("\n", "<br/>"))

        if customer_parts:
            elements.append(Paragraph(
                "<br/>".join(customer_parts),
                self.styles["DetailText"],
            ))
        else:
            elements.append(Paragraph(
                "<i>Customer details to be confirmed</i>",
                self.styles["DetailText"],
            ))

        return elements

    def _build_job_section(
        self,
        job_name: str,
        quantity: int,
        dimensions: dict,
        materials: dict,
        operations: list[str],
    ) -> list:
        """Build the job specification section."""
        elements = []
        elements.append(Paragraph("Job Specification", self.styles["SectionHeader"]))

        # Spec table
        spec_data = [
            ["Job Description", job_name],
            ["Quantity", f"{quantity:,}"],
        ]

        # Dimensions
        flat_w = dimensions.get("flat_width")
        flat_h = dimensions.get("flat_height")
        if flat_w and flat_h:
            spec_data.append(["Flat Size", f"{flat_w}mm x {flat_h}mm"])

        spine = dimensions.get("spine_depth")
        if spine and spine > 0:
            spec_data.append(["Spine Depth", f"{spine}mm"])

        # Materials
        board = materials.get("board_type", "").replace("_", " ").title()
        thickness = materials.get("board_thickness")
        if board:
            board_desc = f"{board}"
            if thickness:
                board_desc += f" ({thickness}mm)"
            spec_data.append(["Board", board_desc])

        outer = materials.get("outer_wrap", "").replace("_", " ").title()
        if outer:
            spec_data.append(["Outer Wrap", outer])

        liner = materials.get("liner", "").replace("_", " ").title()
        if liner:
            spec_data.append(["Liner", liner])

        # Operations
        if operations:
            ops_text = ", ".join(op.replace("_", " ").title() for op in operations)
            spec_data.append(["Operations", ops_text])

        spec_table = Table(
            spec_data,
            colWidths=[45 * mm, 125 * mm],
        )
        spec_table.setStyle(TableStyle([
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
            ("FONT", (1, 0), (1, -1), "Helvetica", 9),
            ("TEXTCOLOR", (0, 0), (0, -1), PackagePro_DARK),
            ("TEXTCOLOR", (1, 0), (1, -1), colors.black),
            ("BACKGROUND", (0, 0), (-1, -1), PackagePro_LIGHT_GREY),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))

        elements.append(spec_table)
        return elements

    def _build_cost_section(self, breakdown: dict[str, Any]) -> list:
        """Build the cost breakdown section."""
        elements = []
        elements.append(Paragraph("Cost Breakdown", self.styles["SectionHeader"]))

        cost_data = [["Item", "Amount (£)"]]

        # Material costs
        material_costs = breakdown.get("material_costs", {})
        if material_costs:
            for mat_name, cost in material_costs.items():
                display_name = mat_name.replace("_", " ").title()
                cost_data.append([display_name, f"£{float(cost):,.2f}"])

        # Labor
        labor_cost = breakdown.get("labor_cost")
        if labor_cost:
            cost_data.append(["Labour", f"£{float(labor_cost):,.2f}"])

        # Overhead
        overhead_cost = breakdown.get("overhead_cost")
        if overhead_cost:
            cost_data.append(["Overhead", f"£{float(overhead_cost):,.2f}"])

        # Wastage
        wastage_cost = breakdown.get("wastage_cost")
        if wastage_cost:
            cost_data.append(["Wastage Allowance", f"£{float(wastage_cost):,.2f}"])

        # Complexity adjustment
        complexity = breakdown.get("complexity_adjustment")
        if complexity and float(complexity) != 0:
            cost_data.append(["Complexity Adjustment", f"£{float(complexity):,.2f}"])

        # Rush premium
        rush = breakdown.get("rush_premium")
        if rush and float(rush) != 0:
            cost_data.append(["Rush Premium", f"£{float(rush):,.2f}"])

        col_widths = [130 * mm, 40 * mm]
        cost_table = Table(cost_data, colWidths=col_widths)
        cost_table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), PackagePro_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            # Data rows
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PackagePro_LIGHT_GREY]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (1, 0), (1, -1), 6),
        ]))

        elements.append(cost_table)
        return elements

    def _build_totals_section(
        self,
        total_cost: Decimal,
        unit_cost: Optional[Decimal],
        quoted_price: Optional[Decimal],
        quantity: int,
        confidence_level: Optional[float],
    ) -> list:
        """Build the totals and pricing section."""
        elements = []
        elements.append(Spacer(1, 3 * mm))

        price = quoted_price or total_cost
        unit = unit_cost or (total_cost / quantity if quantity else total_cost)

        totals_data = []

        if quoted_price and quoted_price != total_cost:
            totals_data.append(["Estimated Cost", f"£{float(total_cost):,.2f}"])

        totals_data.append(["Total Price", f"£{float(price):,.2f}"])
        totals_data.append(["Unit Price", f"£{float(unit):,.4f}"])

        if confidence_level and confidence_level > 0:
            conf_pct = int(confidence_level * 100)
            totals_data.append(["Confidence Level", f"{conf_pct}%"])

        totals_table = Table(
            totals_data,
            colWidths=[130 * mm, 40 * mm],
        )

        style_cmds = [
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
            ("FONT", (1, 0), (1, -1), "Helvetica-Bold", 10),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TEXTCOLOR", (0, 0), (-1, -1), PackagePro_DARK),
            ("LINEABOVE", (0, 0), (-1, 0), 1.5, PackagePro_BLUE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (1, 0), (1, -1), 6),
        ]

        # Highlight the total price row
        total_row = 1 if quoted_price and quoted_price != total_cost else 0
        style_cmds.append(("BACKGROUND", (0, total_row), (-1, total_row), PackagePro_LIGHT_BLUE))
        style_cmds.append(("FONT", (1, total_row), (1, total_row), "Helvetica-Bold", 12))
        style_cmds.append(("TEXTCOLOR", (1, total_row), (1, total_row), PackagePro_BLUE))

        totals_table.setStyle(TableStyle(style_cmds))
        elements.append(totals_table)
        return elements

    def _build_terms_section(self, validity_days: int) -> list:
        """Build the terms and conditions section."""
        elements = []
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("Terms & Conditions", self.styles["SectionHeader"]))

        terms = [
            f"This quotation is valid for {validity_days} days from the date above.",
            "Prices are exclusive of VAT.",
            "Payment terms: 30 days from date of invoice.",
            "Delivery times to be confirmed upon order placement.",
            "Quantities are subject to +/- 5% overs/unders allowance.",
            "All prices are based on the specifications detailed above. "
            "Changes to specifications may result in revised pricing.",
        ]

        for i, term in enumerate(terms, 1):
            elements.append(Paragraph(
                f"{i}. {term}",
                self.styles["DetailText"],
            ))

        return elements

    def _build_footer(self) -> list:
        """Build the document footer."""
        elements = []
        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph(
            f"{self.company_name} | {self.company_phone} | {self.company_email}",
            self.styles["FooterText"],
        ))
        return elements


def generate_quote_pdf(
    estimate: Any,
    customer: Optional[Any] = None,
) -> bytes:
    """
    Convenience function to generate a quote PDF from an Estimate model instance.

    Args:
        estimate: Estimate SQLAlchemy model instance
        customer: Optional Customer model instance

    Returns:
        PDF content as bytes
    """
    generator = QuotePDFGenerator()

    inputs = dict(estimate.inputs) if estimate.inputs else {}
    outputs = dict(estimate.outputs) if estimate.outputs else {}

    customer_name = None
    customer_contact = None
    customer_address = None

    if customer:
        customer_name = customer.name
        customer_contact = customer.contact_name
        customer_address = customer.full_address

    return generator.generate(
        reference_number=estimate.reference_number,
        job_name=estimate.job_name,
        customer_name=customer_name,
        customer_contact=customer_contact,
        customer_address=customer_address,
        quantity=inputs.get("quantity", 0),
        dimensions=inputs.get("dimensions", {}),
        materials=inputs.get("materials", {}),
        operations=inputs.get("operations", []),
        cost_breakdown=outputs,
        total_cost=estimate.total_cost or Decimal("0"),
        unit_cost=estimate.unit_cost,
        quoted_price=estimate.quoted_price,
        confidence_level=estimate.confidence_level,
        notes=estimate.customer_notes,
    )
