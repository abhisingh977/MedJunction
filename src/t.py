from bs4 import BeautifulSoup

with open('file.txt', 'r') as file:
    # Read the entire file content
    file_content = file.read()

    # Print the file content
    print(file_content)

# Parse the HTML content
soup = BeautifulSoup(file_content, 'html.parser')

# Find all rows in the table
rows = soup.find_all('tr')

# Initialize an empty list to store extracted data
hospital_data = []

# Loop through each row and extract the data
for row in rows[1:]:  # skipping the header row
    columns = row.find_all('td')
    sr_no = columns[0].text.strip()
    hospital_name = columns[1].text.strip()
    address = columns[2].text.strip()
    state = columns[3].text.strip()
    city = columns[4].text.strip()
    pin = columns[5].text.strip()
    contact_no = columns[6].text.strip()
    
    # Append the extracted data into the list
    hospital_data.append({
        'Hospital Name': hospital_name,
        'Address': address,
        'State': state,
        'City': city,
    })

# Print the extracted data
for hospital in hospital_data:
    print(hospital)
