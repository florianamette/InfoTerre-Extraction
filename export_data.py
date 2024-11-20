import requests
from bs4 import BeautifulSoup
import re
import json
import csv

# Configuration
FILTERED = True
BASE_URL = "https://infoterre.brgm.fr/rechercher/pagine.htm"
JSESSIONID = "F7553E5D8CEE73B3681B9AD65B9ADB07"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0",
    "Cookie": f"JSESSIONID={JSESSIONID}"
}

def apply_filter():
    url = f"https://infoterre.brgm.fr/rechercher/refine.htm"
    data = {"action": "refine", "id": "carmat_actif:true"}
    response = requests.post(url, headers=HEADERS, data=data)
    if response.status_code == 200:
        print("Filtre appliqué avec succès.")
    else:
        raise Exception(f"Erreur lors de l'application du filtre: {response.status_code}")


def fetch_page_content(page_number=1):
    """
    Envoie une requête POST pour récupérer le contenu d'une page spécifique.
    """
    data = {"page": str(page_number)}
    response = requests.post(BASE_URL, headers=HEADERS, data=data)

    if response.status_code == 200:
        print(f"Page {page_number} récupérée avec succès.")
        return response.text
    else:
        print(f"Erreur lors de la récupération de la page {page_number}: {response.status_code}")
        return None


def get_max_pages(html_content):
    """
    Récupère le nombre maximum de pages à partir du contenu HTML.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    pagination_element = soup.find("span", id="pagination_last")
    if pagination_element:
        # Extraction de la valeur dans le JavaScript
        match = re.search(r"value\s*=\s*'(\d+)'", pagination_element.get("onclick", ""))
        if match:
            return int(match.group(1))
    print("Nombre maximum de pages introuvable, valeur par défaut utilisée (1).")
    return 1


def extract_field(tr_element, label):
    """
    Récupère la valeur d'un champ dans un <tr> en fonction du label fourni.
    """
    field = tr_element.find("font", text=lambda t: t and label in t)
    if field and field.find_next_sibling("font", class_="results_item_field_value"):
        return field.find_next_sibling("font", class_="results_item_field_value").text.strip()
    return None


def extract_additional_data(soup, row_id):
    """
    Récupère les données additionnelles pour une ligne spécifique, identifiée par son ID.
    """
    additional_row = soup.find("tr", id=f"results_item_additional_content_{row_id}_null")
    if not additional_row:
        return {}

    additional_data = {}
    additional_data["Site en activité"] = extract_field(additional_row, "Site en activité")
    additional_data["Exploitation en eau"] = extract_field(additional_row, "Exploitation en eau")
    additional_data["Substances"] = extract_field(additional_row, "Substances")
    additional_data["Produits"] = extract_field(additional_row, "Produits")
    additional_data["Longitude"] = extract_field(additional_row, "Longitude")
    additional_data["Latitude"] = extract_field(additional_row, "Latitude")
    additional_data["Date de fin d'autorisation"] = extract_field(additional_row, "Date de fin d'autorisation")
    return additional_data


def extract_results(html_content):
    """
    Analyse le contenu HTML pour extraire les données principales et additionnelles.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    results = []

    # Recherche des lignes principales
    main_rows = soup.find_all("tr", class_="results_item")
    for row in main_rows:
        result = {}

        # Identifiant de la ligne
        id_element = row.find("a", {"id": lambda x: x and x.startswith("chkItem_")})
        if id_element:
            row_id = id_element["id"].split("_")[1]  # Exemple : 'carmat115602'
            result["Identifiant"] = extract_field(row, "Identifiant")
            result["Numéro S3IC"] = extract_field(row, "Numéro S3IC")
            result["Commune"] = extract_field(row, "Commune")

            # Récupération des données additionnelles
            additional_data = extract_additional_data(soup, row_id)
            result.update(additional_data)

            results.append(result)

    return results


def fetch_all_results():
    """
    Parcourt toutes les pages dynamiquement et récupère toutes les données des résultats.
    """
    # Récupère la première page pour déterminer le nombre maximum de pages
    first_page_content = fetch_page_content()
    max_pages = get_max_pages(first_page_content)
    print(f"Nombre maximum de pages détecté : {max_pages}")

    all_results = []
    for page_number in range(1, max_pages + 1):
        html_content = fetch_page_content(page_number)
        if html_content:
            results = extract_results(html_content)
            all_results.extend(results)

    return all_results


def save_to_json(results, filename="results.json"):
    """
    Sauvegarde les résultats dans un fichier JSON.
    """
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, ensure_ascii=False, indent=4)
    print(f"Résultats sauvegardés dans {filename}")


def save_to_csv(results, filename="results.csv"):
    """
    Sauvegarde les résultats dans un fichier CSV.
    """
    if not results:
        print("Aucun résultat à sauvegarder.")
        return

    with open(filename, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Résultats sauvegardés dans {filename}")


# Main
if __name__ == "__main__":
    try:
        if FILTERED:
            apply_filter()
        # Récupération des résultats sur toutes les pages
        all_results = fetch_all_results()

        # Sauvegarde des résultats en JSON et CSV
        save_to_json(all_results)
        save_to_csv(all_results)
    except Exception as e:
        print(f"Erreur : {e}")