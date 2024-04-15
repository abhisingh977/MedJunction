

let selectedFile;

function handleFileSelect(event) {
    selectedFile = event.target.files[0];
    document.getElementById("fileName").innerText = "File selected: " + selectedFile.name;
}

function uploadFile() {
    if (!selectedFile) {
        alert("Please select a file to upload.");
        return;
    }

    const fileName = document.getElementById("fileNameInput").value.trim();
    if (fileName === "") {
        alert("Please enter a name for the file.");
        return;
    }

    const reportItem = document.createElement("li");
    const reportLink = document.createElement("a");
    reportLink.href = "#"; // You can set the actual link here
    reportLink.textContent = fileName + " " + date;
    reportItem.appendChild(reportLink);
    document.getElementById("previous-reports-history").appendChild(reportItem);

    // Here you can upload the file to the server or perform any other action with it
    // For demonstration, let's just reset the selected file and input fields
    selectedFile = null;
    document.getElementById("fileName").innerText = "";
    document.getElementById("fileInput").value = ""; // Clear the file input
    document.getElementById("fileNameInput").value = ""; // Clear the file name input

}

function saveTextToFlask(text, source) {

    // Concatenate the current date and text
    var textWithDate = text;

    // Send an AJAX request to Flask route to save the entered text
    // You can use fetch or other methods to send the data to Flask
    // Example using fetch:
    fetch('/save_text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: textWithDate, source: source })
    })
        .then(response => {
            if (response.ok) {
                console.log('Text saved successfully.');
            } else {
                console.error('Failed to save text.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}
function toggleEditableTextDate(listId) {
    // Get the ul element
    var ul = document.getElementById(listId);

    // Create a new list item
    var li = document.createElement("li");

    // Create a new paragraph for the current date
    var dateParagraph = document.createElement("p");
    var currentDate = new Date().toLocaleDateString();
    var dateText = document.createTextNode(currentDate);
    dateParagraph.appendChild(dateText);

    // Create an editable input box
    var inputBox = document.createElement("input");
    inputBox.setAttribute("type", "text");
    inputBox.setAttribute("placeholder", "Enter data");

    // Function to adjust input width based on content
    function adjustInputWidth() {
        inputBox.style.height = ((inputBox.value.length + 22) * 1) + '%'; // Adjust width based on content
    }

    // Create a "Save" button
    var saveButton = document.createElement("button");
    saveButton.innerHTML = "Save";
    saveButton.onclick = function () {
        // Get the entered text
        var enteredText = inputBox.value;
        // Send the entered text to Flask route for saving
        saveTextToFlask(enteredText, listId);
        // Make the input box non-editable
        inputBox.setAttribute("readonly", true);
    };


    var discardButton = document.createElement("button");
    discardButton.innerHTML = "Discard";
    discardButton.onclick = function () {
        // Remove the current list item from the UI
        ul.removeChild(li);
        // Send a request to Flask to remove the corresponding text
        discardTextFromFlask(inputBox.value, listId);
    };


    inputBox.addEventListener('input', adjustInputWidth);

    // Append the paragraph, input box, and buttons to the list item
    li.appendChild(dateParagraph);
    li.appendChild(inputBox);
    li.appendChild(saveButton);
    li.appendChild(discardButton);

    // Append the list item to the ul element
    ul.appendChild(li);
    adjustInputWidth();
}


function discardTextFromFlask(text, source) {
    // Send an AJAX request to Flask route to discard the entered text
    // You can use fetch or other methods to send the data to Flask
    // Example using fetch:
    // Get the current date

    // Concatenate the current date and text
    var textWithDate = text;

    fetch('/discard_text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: textWithDate, source: source })
    })
        .then(response => {
            if (response.ok) {
                console.log('Text discarded successfully.');
            } else {
                console.error('Failed to discard text.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function validateForm() {
    var filename = document.getElementById("fileNameInput").value;
    if (filename.trim() === "") {
        alert("Please enter a report name.");
        return false; // Prevent form submission
    }
    return true; // Allow form submission
}