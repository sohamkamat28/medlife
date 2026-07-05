import base64
import io
import mimetypes
import os
import time

from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
from PIL import Image

from data_handler import DEFINITION_NOT_FOUND, GLOSSARY_DATA, get_definition, normalize_term, resolve_definition
from ner_model import analyze_text
from ocr_handler import extract_text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FALLBACK_DEFINITION = "Detected by the medical NER model. A simplified glossary definition is not available yet."

dash_app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": "MedLife analyzes medical report text and images with OCR, NER, and glossary-backed definitions.",
        },
    ],
)
app = dash_app.server
dash_app.title = "MedLife | Medical report analyzer"


def _local_image_data_uri(relative_path: str) -> str | None:
    image_path = os.path.join(BASE_DIR, relative_path)

    if not os.path.exists(image_path):
        return None

    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


REPORT_PREVIEW_SRC = _local_image_data_uri("test/test2.png")


def nav_link(label: str, href: str) -> html.A:
    return html.A(label, href=href, className="nav-link")


def metric(label: str, value: str) -> html.Div:
    return html.Div([
        html.Span(value, className="metric-value"),
        html.Span(label, className="metric-label"),
    ], className="metric")


def notice(kind: str, title: str, body: str = "") -> html.Div:
    children = [html.Strong(title)]
    if body:
        children.append(html.Span(body))

    return html.Div(children, className=f"notice notice--{kind}")


def format_label(label: str) -> str:
    if label == "Glossary Match":
        return "Glossary"

    return str(label).replace("_", " ").replace("-", " ").title()


def display_entity(word: str) -> str:
    record = resolve_definition(word)
    if record:
        return record["entity"]

    return str(word).strip()


def result_table(table_data: list[dict]) -> html.Div:
    return html.Div(
        dash_table.DataTable(
            columns=[{"name": column, "id": column} for column in ["Entity", "Label", "Definition"]],
            data=table_data,
            sort_action="native",
            page_size=8,
            style_as_list_view=True,
            style_table={
                "overflowX": "auto",
                "border": "0",
            },
            style_cell={
                "backgroundColor": "transparent",
                "border": "0",
                "color": "#26332f",
                "fontFamily": "Outfit, ui-sans-serif, system-ui, sans-serif",
                "fontSize": "15px",
                "height": "auto",
                "lineHeight": "1.55",
                "maxWidth": "420px",
                "minWidth": "120px",
                "padding": "16px 14px",
                "textAlign": "left",
                "whiteSpace": "normal",
            },
            style_header={
                "backgroundColor": "#e7efe9",
                "border": "0",
                "color": "#24342f",
                "fontSize": "13px",
                "fontWeight": "700",
                "letterSpacing": "0.04em",
                "textTransform": "uppercase",
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f6f8f5",
                },
                {
                    "if": {"column_id": "Label"},
                    "color": "#17695f",
                    "fontWeight": "700",
                },
                {
                    "if": {"column_id": "Entity"},
                    "fontWeight": "700",
                },
            ],
        ),
        className="result-data-table",
    )


def hero_visual() -> html.Div:
    preview = (
        html.Img(src=REPORT_PREVIEW_SRC, alt="Sample medical report text preview")
        if REPORT_PREVIEW_SRC
        else html.Div("Report preview", className="preview-fallback")
    )

    return html.Div([
        html.Div([
            html.Div([
                html.Span("Report scan", className="eyebrow"),
                html.Span("OCR ready", className="scan-status"),
            ], className="preview-toolbar"),
            html.Div(preview, className="preview-image"),
            html.Div([
                html.Div([html.Span("Patient"), html.Strong("Name detected")]),
                html.Div([html.Span("Terms"), html.Strong("Glossary matched")]),
                html.Div([html.Span("Output"), html.Strong("Readable table")]),
            ], className="preview-stats"),
        ], className="report-preview"),
    ], className="hero-visual")


dash_app.layout = html.Div([
    html.A("Skip to analyzer", href="#workspace", className="skip-link"),

    html.Header([
        html.Nav([
            html.A([
                html.Span("M", className="brand-mark"),
                html.Span("MedLife", className="brand-name"),
            ], href="#top", className="brand"),
            html.Div([
                nav_link("Analyzer", "#workspace"),
                nav_link("Results", "#results"),
                nav_link("Glossary", "#results"),
            ], className="nav-links"),
        ], className="top-nav"),
    ], className="site-header", id="top"),

    html.Main([
        html.Section([
            html.Div([
                html.P("Medical report analyzer", className="eyebrow"),
                html.H1("Read reports faster, without losing the clinical context."),
                html.P(
                    "Upload a report image or paste text. MedLife extracts readable text, detects medical terms, and connects them to simplified glossary definitions.",
                    className="hero-copy",
                ),
                html.Div([
                    html.A("Start analysis", href="#workspace", className="button-link button-link--primary"),
                    html.A("See output", href="#results", className="button-link button-link--secondary"),
                ], className="hero-actions"),
            ], className="hero-content"),
            hero_visual(),
        ], className="hero-section"),

        html.Section([
            metric("OCR paths", "3"),
            metric("Glossary entries", str(len(GLOSSARY_DATA))),
            metric("Inputs", "Text + image"),
        ], className="metrics-strip", **{"aria-label": "Analyzer summary"}),

        html.Section([
            html.Div([
                html.P("Workspace", className="eyebrow"),
                html.H2("Analyze a medical report"),
                html.P(
                    "The uploaded image text is placed into the report box first, so you can review it before running analysis.",
                    className="section-copy",
                ),
            ], className="section-heading"),

            html.Div([
                html.Div([
                    html.Label("Upload report image", className="field-label"),
                    dcc.Upload(
                        id="upload-image",
                        children=html.Div([
                            html.Span("Drop an image here", className="upload-title"),
                            html.Span("PNG, JPG, or scanned report snippets", className="upload-subtitle"),
                        ], className="upload-copy"),
                        className="upload-zone",
                        multiple=False,
                    ),
                ], className="input-panel input-panel--upload"),

                html.Div([
                    html.Label("Report text", htmlFor="input-text", className="field-label"),
                    dcc.Textarea(
                        id="input-text",
                        placeholder="Paste report text here, or upload an image to extract it automatically...",
                        className="report-textarea",
                        spellCheck=False,
                    ),
                ], className="input-panel input-panel--text"),
            ], className="analyzer-grid"),

            html.Div([
                html.Button("Analyze report", id="analyze-btn", className="analyze-button", n_clicks=0),
                html.P("Educational support only. Always confirm findings with a qualified clinician.", className="fine-print"),
            ], className="action-row"),
        ], className="workspace-section", id="workspace"),

        html.Section([
            html.Div([
                html.P("Results", className="eyebrow"),
                html.H2("Detected terms"),
            ], className="section-heading section-heading--compact"),
            dcc.Loading(
                id="loading-output",
                type="dot",
                color="#17695f",
                children=html.Div(
                    notice("empty", "No report analyzed yet", "Upload an image or paste text, then run analysis."),
                    id="output",
                    className="output-area",
                ),
            ),
        ], className="results-section", id="results"),
    ], className="site-main"),

    html.Footer([
        html.Span("MedLife"),
        html.Span("Built for clear report review, not medical diagnosis."),
    ], className="site-footer"),
], className="site-shell")


@dash_app.callback(
    Output("input-text", "value", allow_duplicate=True),
    Output("output", "children"),
    Input("analyze-btn", "n_clicks"),
    Input("upload-image", "contents"),
    State("input-text", "value"),
    prevent_initial_call=True,
)
def analyze(n_clicks, image_data, text_input):
    ctx = callback_context
    if not ctx.triggered:
        return text_input, html.Div()

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    current_text = text_input if text_input else ""

    if trigger_id == "upload-image" and image_data is not None:
        temp_path = ""

        try:
            _, content_string = image_data.split(",", 1)
            decoded = base64.b64decode(content_string)

            temp_path = f"temp_upload_{time.time_ns()}.png"
            image = Image.open(io.BytesIO(decoded))
            image.save(temp_path)

            ocr_text = extract_text(temp_path)
            error_prefixes = ("Tesseract executable", "Image file not found", "Error processing image")

            if not ocr_text.strip():
                return current_text, notice("warning", "No text found", "Try a sharper image or paste the report text directly.")

            if ocr_text.startswith(error_prefixes):
                return current_text, notice("error", "Image processing failed", ocr_text)

            return ocr_text, notice("success", "Text extracted", "Review the report text, then run analysis.")

        except Exception as e:
            return current_text, notice("error", "Image processing failed", str(e))

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    if trigger_id == "analyze-btn":
        if not current_text.strip():
            return current_text, notice("warning", "Report text is empty", "Paste text or upload an image first.")

        patient_name, results = analyze_text(current_text)

        if not results:
            return current_text, notice(
                "success",
                "No specialized terms found",
                "The report text was readable, but no glossary or biomedical NER matches were detected.",
            )

        display_name = patient_name.title() if patient_name else "Name not found"
        table_data = []
        seen_rows = set()

        for word, label in results:
            entity = display_entity(word)
            definition = get_definition(word)

            if definition == DEFINITION_NOT_FOUND:
                definition = FALLBACK_DEFINITION

            row_key = normalize_term(entity)
            if not row_key or row_key in seen_rows:
                continue

            table_data.append({
                "Entity": entity,
                "Label": format_label(label),
                "Definition": definition,
            })
            seen_rows.add(row_key)

        if not table_data:
            return current_text, notice(
                "success",
                "No glossary matches found",
                "The text was processed, but no recognized medical terms were available to display.",
            )

        patient_card = html.Div([
            html.Div([
                html.Span("Patient", className="patient-label"),
                html.Strong(display_name, className="patient-name"),
            ]),
            html.Div([
                html.Span(str(len(table_data)), className="result-count"),
                html.Span("terms detected", className="result-count-label"),
            ], className="result-count-box"),
        ], className="patient-summary")

        return current_text, html.Div([
            patient_card,
            result_table(table_data),
        ], className="results-panel")

    return current_text, html.Div()


if __name__ == "__main__":
    dash_app.run(debug=True)
