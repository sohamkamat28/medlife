import mimetypes

from dash import (
    ClientsideFunction,
    Dash,
    Input,
    Output,
    State,
    callback_context,
    dash_table,
    dcc,
    html,
)
from flask import Response, request

from data_handler import (
    DEFINITION_NOT_FOUND,
    GLOSSARY_DATA,
    get_definition,
    normalize_term,
    resolve_definition,
)
from ner_model import analyze_text

FALLBACK_DEFINITION = "Detected by the medical NER model. A simplified glossary definition is not available yet."
SITE_URL = "https://medlife-topaz.vercel.app"
SITE_DESCRIPTION = "Upload a medical report or paste its text to find key terms and clear, glossary-backed definitions with MedLife."

mimetypes.add_type("font/woff2", ".woff2")

dash_app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": SITE_DESCRIPTION,
        },
        {"name": "theme-color", "content": "#f5f7f6"},
        {"property": "og:type", "content": "website"},
        {"property": "og:site_name", "content": "MedLife"},
        {"property": "og:title", "content": "MedLife | Understand your medical report"},
        {"property": "og:description", "content": SITE_DESCRIPTION},
        {"property": "og:url", "content": SITE_URL},
        {
            "property": "og:image",
            "content": f"{SITE_URL}/assets/images/medlife-family-report.webp",
        },
        {"name": "twitter:card", "content": "summary_large_image"},
    ],
)
app = dash_app.server
dash_app.title = "MedLife | Understand your medical report"

dash_app.index_string = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    <link rel="preload" href="/assets/fonts/Geist-Variable.woff2" as="font" type="font/woff2" crossorigin>
    <link
      rel="preload"
      href="/assets/images/medlife-family-report.webp"
      as="image"
      fetchpriority="high"
      imagesrcset="/assets/images/medlife-family-report-640.webp 640w, /assets/images/medlife-family-report-800.webp 800w, /assets/images/medlife-family-report.webp 1200w"
      imagesizes="(max-width: 820px) calc(100vw - 2rem), (max-width: 1240px) 50vw, 560px"
    >
    {{%css%}}
  </head>
  <body>
    <a class="skip-link" href="#workspace">Skip to analyzer</a>
    <header class="site-header" id="top">
      <nav class="top-nav" aria-label="Primary navigation">
        <a class="brand" href="#top" aria-label="MedLife home">
          <span class="brand-mark" aria-hidden="true">M</span>
          <span class="brand-name">MedLife</span>
        </a>
        <div class="nav-links">
          <a class="nav-link" href="#workspace">Analyzer</a>
          <a class="nav-link" href="#results">Results</a>
          <a class="nav-link" href="#results">Glossary</a>
        </div>
        <a class="nav-cta" href="#workspace">Analyze report</a>
      </nav>
    </header>

    <main class="site-main">
      <section class="hero-section" aria-labelledby="hero-title">
        <div class="hero-content">
          <p class="eyebrow">Medical report analyzer</p>
          <h1 id="hero-title">Understand your medical report.</h1>
          <p class="hero-copy">Upload an image or paste text to find key terms and plain-language definitions in seconds.</p>
          <div class="hero-actions">
            <a class="button-link button-link--primary" href="#workspace">Analyze report</a>
            <a class="text-link" href="#how-it-works">How it works</a>
          </div>
        </div>
        <figure class="hero-figure">
          <img
            src="/assets/images/medlife-family-report.webp"
            srcset="/assets/images/medlife-family-report-640.webp 640w, /assets/images/medlife-family-report-800.webp 800w, /assets/images/medlife-family-report.webp 1200w"
            sizes="(max-width: 820px) calc(100vw - 2rem), (max-width: 1240px) 50vw, 560px"
            width="1200"
            height="900"
            alt="A daughter and her father reviewing a medical report together at home"
            fetchpriority="high"
            decoding="async"
          >
        </figure>
      </section>

      <section class="process-section" id="how-it-works" aria-label="How MedLife works">
        <div class="process-intro">
          <h2>From report to plain language.</h2>
          <p>A focused flow that keeps you in control of what gets analyzed.</p>
        </div>
        <ol class="process-list">
          <li><strong>Add your report</strong><span>Upload an image or paste the text directly.</span></li>
          <li><strong>Review the text</strong><span>Check the OCR result before analysis begins.</span></li>
          <li><strong>Explore key terms</strong><span>Match report language with {len(GLOSSARY_DATA):,} glossary entries.</span></li>
        </ol>
      </section>

      {{%app_entry%}}
    </main>

    <footer class="site-footer">
      <div class="footer-brand">
        <span class="brand-mark brand-mark--small" aria-hidden="true">M</span>
        <span class="brand-name">MedLife</span>
      </div>
      <p>Built for clearer report conversations, not medical diagnosis.</p>
      <nav class="footer-links" aria-label="Footer navigation">
        <a href="#workspace">Analyzer</a>
        <a href="#results">Results</a>
        <a href="#privacy">Privacy</a>
        <a href="#disclaimer">Medical disclaimer</a>
      </nav>
    </footer>

    <footer hidden>
      {{%config%}}
      {{%scripts%}}
      {{%renderer%}}
    </footer>
  </body>
</html>"""


@app.route("/robots.txt")
def robots_txt() -> Response:
    return Response(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n",
        mimetype="text/plain",
    )


@app.route("/sitemap.xml")
def sitemap_xml() -> Response:
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{SITE_URL}/</loc></url>"
        "</urlset>"
    )
    return Response(sitemap, mimetype="application/xml")


@app.route("/llms.txt")
def llms_txt() -> Response:
    content = f"""# MedLife

> A medical report analyzer that identifies key terms and provides glossary-backed definitions.

## Main page

- [MedLife]({SITE_URL}/): Upload a report image or paste report text for analysis.

## Important

MedLife is educational support. It does not diagnose conditions or replace advice from a qualified clinician.
"""
    return Response(content, mimetype="text/plain")


@app.after_request
def add_response_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if request.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

    return response


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
            columns=[
                {"name": column, "id": column}
                for column in ["Entity", "Label", "Definition"]
            ],
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
                "color": "#1c2925",
                "fontFamily": "Geist, ui-sans-serif, system-ui, sans-serif",
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
                "backgroundColor": "#e4eeea",
                "border": "0",
                "color": "#1c2925",
                "fontSize": "13px",
                "fontWeight": "700",
                "letterSpacing": "0.04em",
                "textTransform": "uppercase",
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f3f7f5",
                },
                {
                    "if": {"column_id": "Label"},
                    "color": "#146c5b",
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


dash_app.layout = html.Div(
    [
        html.Section(
            [
                html.Div(
                    [
                        html.H2("Start with your report."),
                        html.P(
                            "Use whichever input is easiest. Uploaded image text appears in the report box for review first.",
                            className="section-copy",
                        ),
                    ],
                    className="section-heading",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span(
                                    "Upload report image",
                                    className="field-label",
                                    id="upload-label",
                                ),
                                dcc.Upload(
                                    id="upload-image",
                                    children=html.Div(
                                        [
                                            html.Span(
                                                "+",
                                                className="upload-symbol",
                                                **{"aria-hidden": "true"},
                                            ),
                                            html.Span(
                                                "Drop your report here",
                                                className="upload-title",
                                            ),
                                            html.Span(
                                                "or choose a PNG or JPG file",
                                                className="upload-subtitle",
                                            ),
                                        ],
                                        className="upload-copy",
                                    ),
                                    className="upload-zone",
                                    accept="image/png,image/jpeg",
                                    multiple=False,
                                ),
                            ],
                            className="input-panel input-panel--upload",
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Report text",
                                    htmlFor="input-text",
                                    className="field-label",
                                ),
                                dcc.Textarea(
                                    id="input-text",
                                    placeholder="Paste report text here, or upload an image to extract it automatically.",
                                    className="report-textarea",
                                    spellCheck=False,
                                ),
                            ],
                            className="input-panel input-panel--text",
                        ),
                    ],
                    className="analyzer-grid",
                ),
                html.Div(
                    [
                        html.Button(
                            "Analyze report",
                            id="analyze-btn",
                            className="analyze-button",
                            n_clicks=0,
                        ),
                        html.P(
                            "Educational support only. Always confirm findings with a qualified clinician.",
                            className="fine-print",
                        ),
                    ],
                    className="action-row",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3("Your results"),
                                html.P(
                                    "Detected terms and glossary definitions will appear below."
                                ),
                            ],
                            className="results-heading",
                        ),
                        dcc.Loading(
                            id="loading-output",
                            custom_spinner=html.Div(
                                [
                                    html.Span(
                                        "Reading report", className="skeleton-label"
                                    ),
                                    html.Div(
                                        className="skeleton-line skeleton-line--wide"
                                    ),
                                    html.Div(className="skeleton-line"),
                                    html.Div(
                                        className="skeleton-line skeleton-line--short"
                                    ),
                                ],
                                className="results-skeleton",
                                role="status",
                            ),
                            children=html.Div(
                                notice(
                                    "empty",
                                    "No report analyzed yet",
                                    "Upload an image or paste text, then run analysis.",
                                ),
                                id="output",
                                className="output-area",
                                **{"aria-live": "polite"},
                            ),
                        ),
                    ],
                    className="results-dock",
                    id="results",
                ),
            ],
            className="workspace-section",
            id="workspace",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.H2("Clarity without false certainty."),
                        html.P(
                            "MedLife helps you prepare better questions for your clinician. It does not diagnose conditions or replace medical advice."
                        ),
                    ],
                    className="trust-copy",
                ),
                html.Div(
                    [
                        html.Article(
                            [
                                html.H3("Review before analysis"),
                                html.P(
                                    "Image text is extracted in your browser and shown to you before you continue."
                                ),
                            ]
                        ),
                        html.Article(
                            [
                                html.H3("No saved report history"),
                                html.P(
                                    "MedLife does not create an account or store a report library for you."
                                ),
                            ],
                            id="privacy",
                        ),
                        html.Article(
                            [
                                html.H3("Medical guidance stays human"),
                                html.P(
                                    "Always discuss report findings and next steps with a qualified clinician."
                                ),
                            ],
                            id="disclaimer",
                        ),
                    ],
                    className="trust-list",
                ),
            ],
            className="trust-section",
        ),
    ],
    className="dash-content",
)


@dash_app.callback(
    Output("input-text", "value", allow_duplicate=True),
    Output("output", "children", allow_duplicate=True),
    Input("analyze-btn", "n_clicks"),
    State("input-text", "value"),
    prevent_initial_call=True,
)
def analyze(n_clicks, text_input):
    ctx = callback_context
    if not ctx.triggered:
        return text_input, html.Div()

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    current_text = text_input if text_input else ""

    if trigger_id == "analyze-btn":
        if not current_text.strip():
            return current_text, notice(
                "warning",
                "Report text is empty",
                "Paste text or upload an image first.",
            )

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

            table_data.append(
                {
                    "Entity": entity,
                    "Label": format_label(label),
                    "Definition": definition,
                }
            )
            seen_rows.add(row_key)

        if not table_data:
            return current_text, notice(
                "success",
                "No glossary matches found",
                "The text was processed, but no recognized medical terms were available to display.",
            )

        patient_card = html.Div(
            [
                html.Div(
                    [
                        html.Span("Patient", className="patient-label"),
                        html.Strong(display_name, className="patient-name"),
                    ]
                ),
                html.Div(
                    [
                        html.Span(str(len(table_data)), className="result-count"),
                        html.Span("terms detected", className="result-count-label"),
                    ],
                    className="result-count-box",
                ),
            ],
            className="patient-summary",
        )

        return current_text, html.Div(
            [
                patient_card,
                result_table(table_data),
            ],
            className="results-panel",
        )

    return current_text, html.Div()


dash_app.clientside_callback(
    ClientsideFunction(namespace="medlife_ocr", function_name="extractTextFromUpload"),
    Output("input-text", "value", allow_duplicate=True),
    Output("output", "children", allow_duplicate=True),
    Input("upload-image", "contents"),
    State("input-text", "value"),
    prevent_initial_call=True,
)


if __name__ == "__main__":
    dash_app.run(debug=True)
