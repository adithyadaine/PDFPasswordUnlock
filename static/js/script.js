// static/js/script.js
const uploadForm = document.getElementById("upload-form");
const submitButton = document.getElementById("submit-button");
const buttonText = submitButton.querySelector(".button-text");
const spinner = submitButton.querySelector(".spinner-border");
const messageArea = document.getElementById("message-area");
const fileInput = document.getElementById("pdf_file");

// Function to display messages
function displayMessage(message, category = "danger") {
  // Clear previous messages
  messageArea.innerHTML = "";
  // Create new alert
  const wrapper = document.createElement("div");
  wrapper.innerHTML = [
    `<div class="alert alert-${category} alert-dismissible fade show" role="alert">`,
    `   <div>${message}</div>`,
    '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
    "</div>",
  ].join("");
  messageArea.append(wrapper);
}

// Update button text on file selection (optional but nice)
fileInput.addEventListener("change", function (e) {
  const fileName = e.target.files[0]?.name;
  const defaultText = "Unlock PDF";
  if (fileName) {
    buttonText.textContent = `Unlock ${fileName}`;
  } else {
    buttonText.textContent = defaultText;
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault(); // Prevent default form submission

  // Basic client-side check
  if (!fileInput.files || fileInput.files.length === 0) {
    displayMessage("Please select a PDF file.", "warning");
    return;
  }

  // Show loading state
  buttonText.textContent = "Processing...";
  spinner.style.display = "inline-block";
  submitButton.disabled = true;
  messageArea.innerHTML = ""; // Clear previous messages

  const formData = new FormData(uploadForm);

  try {
    const response = await fetch("/", {
      // Send to the same URL
      method: "POST",
      body: formData,
      // No 'Content-Type' header needed; browser sets it for FormData
    });

    // Try to parse JSON regardless of status code for error messages
    let data;
    try {
      data = await response.json();
    } catch (jsonError) {
      // Handle cases where response is not JSON (e.g., unexpected server error HTML page)
      console.error("Failed to parse JSON response:", jsonError);
      displayMessage(
        `Server returned an unexpected response (Status: ${response.status}). Please try again.`,
        "danger",
      );
      return; // Exit after handling non-JSON response
    }

    if (!response.ok) {
      // Display error from JSON payload if available, else generic
      displayMessage(
        data.error || `An error occurred (Status: ${response.status}).`,
        "danger",
      );
    } else {
      // Success case
      if (data.success && data.download_id) {
        displayMessage(data.message, "success");
        // Trigger download
        window.location.href = `/download/${data.download_id}`;
      } else {
        // Handle unexpected success response format
        console.error("Unexpected success response format:", data);
        displayMessage(
          "Processing completed, but download link is missing.",
          "warning",
        );
      }
    }
  } catch (error) {
    // Handle network errors or other fetch issues
    console.error("Fetch Error:", error);
    displayMessage(
      "A network error occurred. Please check your connection and try again.",
      "danger",
    );
  } finally {
    // Reset button state
    const fileName = fileInput.files[0]?.name;
    buttonText.textContent = fileName ? `Unlock ${fileName}` : "Unlock PDF";
    spinner.style.display = "none";
    submitButton.disabled = false;
  }
});