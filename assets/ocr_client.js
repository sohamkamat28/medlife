(() => {
  const applyUploadLabel = () => {
    const input = document.querySelector("#upload-image input[type='file']");
    if (!input) {
      return false;
    }

    input.setAttribute("aria-labelledby", "upload-label");
    return true;
  };

  const start = () => {
    if (applyUploadLabel()) {
      return;
    }

    const observer = new MutationObserver(() => {
      if (applyUploadLabel()) {
        observer.disconnect();
      }
    });

    observer.observe(document.documentElement, { childList: true, subtree: true });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();

window.dash_clientside = Object.assign({}, window.dash_clientside, {
  medlife_ocr: {
    extractTextFromUpload: async function (contents, currentText) {
      const notice = (kind, title, body) => ({
        namespace: "dash_html_components",
        type: "Div",
        props: {
          className: `notice notice--${kind}`,
          children: [
            {
              namespace: "dash_html_components",
              type: "Strong",
              props: { children: title },
            },
            {
              namespace: "dash_html_components",
              type: "Span",
              props: { children: body },
            },
          ],
        },
      });

      const loadTesseract = () =>
        new Promise((resolve, reject) => {
          if (window.Tesseract) {
            resolve(window.Tesseract);
            return;
          }

          const existingScript = document.querySelector("script[data-medlife-tesseract]");
          if (existingScript) {
            existingScript.addEventListener("load", () => resolve(window.Tesseract), { once: true });
            existingScript.addEventListener("error", reject, { once: true });
            return;
          }

          const script = document.createElement("script");
          script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
          script.async = true;
          script.dataset.medlifeTesseract = "true";
          script.onload = () => resolve(window.Tesseract);
          script.onerror = () => reject(new Error("Unable to load browser OCR library."));
          document.head.appendChild(script);
        });

      if (!contents) {
        return [
          currentText || "",
          notice("empty", "No report analyzed yet", "Upload an image or paste text, then run analysis."),
        ];
      }

      try {
        const Tesseract = await loadTesseract();
        const result = await Tesseract.recognize(contents, "eng", {
          logger: function () {},
        });
        const text = (result && result.data && result.data.text ? result.data.text : "").trim();

        if (!text) {
          return [
            currentText || "",
            notice("warning", "No text found", "Try a sharper image or paste the report text directly."),
          ];
        }

        return [
          text,
          notice("success", "Text extracted", "Review the report text, then run analysis."),
        ];
      } catch (error) {
        return [
          currentText || "",
          notice(
            "error",
            "Image processing failed",
            error && error.message ? error.message : "Browser OCR could not read this image."
          ),
        ];
      }
    },
  },
});
