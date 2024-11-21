import csv
import os
import json

def merge_json_files(input_folder: str, output_file: str):
    """
    Merges all JSON files in the specified folder into a single JSON file.

    Args:
        input_folder (str): The folder containing JSON files to merge.
        output_file (str): The path for the merged JSON file.

    Raises:
        ValueError: If any JSON file contains invalid JSON.
    """
    merged_data = []

    # Iterate through all files in the input folder
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.json'):  # Process only JSON files
            file_path = os.path.join(input_folder, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    # Append the data to merged_data
                    if isinstance(data, list):
                        merged_data.extend(data)
                    else:
                        merged_data.append(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in file {file_name}: {e}")

    # Write the merged data to the output file
    with open(output_file, 'w', encoding='utf-8') as output_json_file:
        json.dump(merged_data, output_json_file, indent=4)

    print(f"All JSON files have been merged into {output_file}")

def convert_json_to_csv(json_filename, csv_filename):
    """
    Convertit les données d'un fichier JSON en fichier CSV.
    """
    try:
        with open(json_filename, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)

        if not data:
            print("Aucune donnée à convertir en CSV.")
            return

        # Collect all unique keys
        all_fieldnames = set()
        for result in data:
            all_fieldnames.update(result.keys())

        # Write to CSV
        with open(csv_filename, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=sorted(all_fieldnames))  # Sort keys for consistent order
            writer.writeheader()
            writer.writerows(data)

        print(f"Résultats convertis en CSV et sauvegardés dans {csv_filename}.")
    except Exception as e:
        print(f"Erreur lors de la conversion JSON -> CSV : {e}")


# Main
if __name__ == "__main__":
    input_folder = "output"
    output_file = "merged_data.json"
    try:
        merge_json_files(input_folder, output_file)
        convert_json_to_csv('merged_data.json', 'merged_data.csv')
    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")