# app.py
import base64
from dash import Dash ,dcc, html , Input , Output, callback , dash_table, callback_context
import io
from PIL import Image
from ocr_handler import extract_text
from ner_model import analyze_text
from data_handler import get_definition # Assuming DEFINITION_NOT_FOUND is still defined in data_handler
import os
import time

app = Dash(__name__, suppress_callback_exceptions=True)

# Define the new color palette for depth
DARK_GREEN_BG = '#E8F5E9' # Darker green for overall page background
LIGHT_GREEN_BOX = '#FFFFFF' # White or very light green for the content box
PASTEL_ACCENT = '#8DD7BF' # Mint green accent
PASTEL_STRIPE = '#F0FFF0'
TEXT_COLOR = '#333333'

app.title = "Medical Report Analyzer"

# Header Bar Layout
header_bar = html.Div(
    "Medical Report Analyzer",
    style={
        'backgroundColor': PASTEL_ACCENT,
        'color': TEXT_COLOR,
        'fontSize': '28px',
        'fontWeight': '700',
        'padding': '15px 0',
        'textAlign': 'center',
        'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.1)',
        'position': 'sticky',
        'top': '0',
        'zIndex': '1000',
        'fontFamily': 'Inter, sans-serif',
        'borderBottom': f'3px solid {TEXT_COLOR}'
    }
)

app.layout = html.Div([
    header_bar,

    html.Div([
        html.H2("Analyze Your Medical Report", style={'color': TEXT_COLOR, 'marginBottom': '15px'}),
        html.P("Enter text or upload an image report.", style={'color': TEXT_COLOR, 'marginBottom': '20px'}),

        dcc.Upload(
            id='upload-image',
            children=html.Div(['📤 Drag and drop or click to upload an image']),
            style={
                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '2px', 'borderStyle': 'dashed',
                'borderColor': PASTEL_ACCENT,
                'borderRadius': '10px', 'textAlign': 'center', 'marginBottom': '15px',
                'cursor': 'pointer', 'backgroundColor': LIGHT_GREEN_BOX, 'color': TEXT_COLOR
            }
        ),

        dcc.Textarea(
            id='input-text',
            placeholder='Or type/paste your medical report here...',
            style={
                'width': '100%', 'height': 150, 'marginBottom': 20,
                'borderRadius': '8px',
                'border': f'1px solid {PASTEL_ACCENT}',
                'padding': '10px',
                'boxShadow': 'inset 0 1px 3px rgba(0, 0, 0, 0.05)',
                'fontFamily': 'Inter, sans-serif',
                'textAlign': 'left'
            }
        ),

        html.Div([
            html.Button("Analyze Report", id='analyze-btn', style={
                'backgroundColor': PASTEL_ACCENT,
                'color': TEXT_COLOR,
                'padding': '15px 40px',
                'borderRadius': '10px',
                'border': 'none',
                'cursor': 'pointer',
                'fontWeight': 'bold',
                'fontSize': '18px',
                'boxShadow': '0 6px 10px rgba(0, 0, 0, 0.15)',
                'transition': 'background-color 0.3s',
                'textTransform': 'uppercase',
                'minWidth': '300px',
                'display': 'inline-block'
            }),
        ], style={'textAlign': 'center', 'marginBottom': 20}),

        html.Div(id='output', style={'marginTop': 30, 'fontFamily': 'Inter, sans-serif'})

    ], style={
        'backgroundColor': LIGHT_GREEN_BOX,
        'padding': '30px',
        'maxWidth': '800px',
        'margin': '30px auto',
        'borderRadius': '15px',
        'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)',
        'textAlign': 'center',
    }),

], style={
    'backgroundColor': DARK_GREEN_BG,
    'minHeight': '100vh',
    'fontFamily': 'Inter, sans-serif'
})


# Define the constant for missing definition (based on data_handler.py)
DEFINITION_NOT_FOUND = "Glossary data not loaded."

@app.callback(
    Output('input-text', 'value', allow_duplicate=True),
    Output('output', 'children'),
    Input('analyze-btn', 'n_clicks'),
    Input('input-text', 'value'),
    Input('upload-image', 'contents'),
    prevent_initial_call=True
)
def analyze(n_clicks, text_input, image_data):
    ctx = callback_context
    if not ctx.triggered:
        return text_input, html.Div()

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    current_text = text_input if text_input else ""

    # --- 1. OCR & Upload Confirmation Triggered by dcc.Upload ---
    if trigger_id == 'upload-image' and image_data is not None:
        try:
            content_type, content_string = image_data.split(',')
            decoded = base64.b64decode(content_string)

            temp_path = f"temp_upload_{time.time()}.png"
            image = Image.open(io.BytesIO(decoded))
            image.save(temp_path)

            ocr_text = extract_text(temp_path)
            os.remove(temp_path)

            confirm_message = html.Div("✅ Image uploaded and text extracted. Click 'Analyze Report'.",
                                        style={'color': '#5cb85c', 'padding': '10px', 'border': '1px solid #5cb85c', 'borderRadius': '5px', 'backgroundColor': '#edf9ed', 'marginBottom': '20px'})

            return ocr_text, confirm_message

        except Exception as e:
            error_message = f"🚨 Error processing image. Ensure required OCR dependencies are installed (e.g., pytesseract executable or easyocr): {e}"
            error_div = html.Div(error_message, style={'color': '#d9534f', 'padding': '10px', 'border': '1px solid #d9534f', 'borderRadius': '5px', 'backgroundColor': '#f9eaea', 'marginBottom': '20px'})
            return current_text, error_div

    # --- 2. Analysis Triggered by Button (`analyze-btn`) ---
    elif trigger_id == 'analyze-btn':
        if not current_text.strip():
            return current_text, html.Div("⚠️ Please enter text or upload an image.", style={'color': '#d9534f', 'padding': '10px', 'border': '1px solid #d9534f', 'borderRadius': '5px', 'backgroundColor': '#f9eaea', 'marginBottom': '20px'})

        patient_name, results = analyze_text(current_text)

        if not results:
            return current_text, html.Div("✅ No specialized medical terms found in the provided text.", style={'color': '#5cb85c', 'padding': '10px', 'border': '1px solid #5cb85c', 'borderRadius': '5px', 'backgroundColor': '#edf9ed'})

        # --- Generate Patient Card ---
        display_name = patient_name.title() if patient_name else "Name Not Found"

        patient_card = html.Div([
            html.H4("Patient Information", style={'color': TEXT_COLOR, 'marginBottom': '5px', 'fontSize': '20px'}),
            html.H3(display_name,
                    style={'color': PASTEL_ACCENT, 'fontSize': '32px', 'fontWeight': 'bold', 'textTransform': 'uppercase'})
        ], style={
            'backgroundColor': PASTEL_STRIPE,
            'padding': '15px 25px',
            'borderRadius': '10px',
            'marginBottom': '25px',
            'border': f'2px solid {PASTEL_ACCENT}',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.08)'
        })

        # --- Prepare Table Data (with Filtering) ---
        table_data = []
        for word, label in results:
            definition = get_definition(word)

            # --- NEW FILTERING LOGIC ---
            if definition == DEFINITION_NOT_FOUND:
                continue

            display_word = word.title() if label != "Abbreviation" else word.upper()

            table_data.append({
                "Entity": display_word,
                "Label": label,
                "Definition": definition
            })

        # Check if all entities were filtered out
        if not table_data:
            return current_text, html.Div("✅ Medical terms were found, but none matched an entry in the simplified glossary.",
                                          style={'color': '#5cb85c', 'padding': '10px', 'border': '1px solid #5cb85c', 'borderRadius': '5px', 'backgroundColor': '#edf9ed', 'marginBottom': '20px'})

        # --- Return Output (Card + Table) ---
        return current_text, html.Div([
            patient_card,
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in ["Entity", "Label", "Definition"]],
                data=table_data,
                style_table={"overflowX": "auto", "border": f"1px solid {PASTEL_ACCENT}", "borderRadius": "8px", "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.05)"},
                style_cell={
                    "textAlign": "left", "padding": "12px", "fontFamily": "Inter, sans-serif",
                    "color": TEXT_COLOR, "whiteSpace": "normal", "height": "auto",
                    "minWidth": "80px", "width": "150px", "maxWidth": "350px",
                },
                style_header={
                    "backgroundColor": PASTEL_ACCENT, "color": TEXT_COLOR, "fontWeight": "bold",
                    "fontSize": "16px", "borderBottom": f"2px solid {PASTEL_ACCENT}"
                },
                style_data_conditional=[
                    {"if": {"column_id": "Label"}, "textAlign": "center", "fontWeight": "600"},
                    {"if": {"row_index": "odd"}, "backgroundColor": PASTEL_STRIPE}
                ],
                page_size=10,
                sort_action="native"
            )
        ], style={'textAlign': 'center'})

    return current_text, html.Div()
if __name__ == '__main__':
    app.run(debug=True)