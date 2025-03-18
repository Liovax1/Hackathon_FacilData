from flask import Flask, request, jsonify, render_template
import pandas as pd
import re
import os
import json
from mistralai import Mistral, UserMessage
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer la clé API
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("La clé API Mistral n'est pas définie dans le fichier .env.")

# Initialiser le client Mistral
client = Mistral(api_key=api_key)
model = "mistral-large-latest"

app = Flask(__name__)

# 📌 Chargement du fichier CSV
CSV_FILE = "Hackathon/data/cleaned_merged_equipment_intervention.csv"

try:
    data_df = pd.read_csv(CSV_FILE, sep=";", encoding="ISO-8859-1")
except UnicodeDecodeError:
    data_df = pd.read_csv(CSV_FILE, sep=";", encoding="utf-8")

# 🔧 Nettoyage des colonnes
data_df.columns = data_df.columns.str.replace('[^A-Za-z0-9_]', '_', regex=True).str.strip()

# 📌 Convertir le DataFrame en dictionnaire pour le prompt
# Limiter à un nombre raisonnable d'entrées pour ne pas dépasser les limites du prompt
max_entries = 500  # Ajustez selon la taille de votre CSV et les limites de Mistral
equipment_dict = {}

# Créer un dictionnaire où la clé est l'ID de l'équipement
for _, row in data_df.head(max_entries).iterrows():
    equip_nom = row.get('Nom', 'nom inconnu')
    equip_id = row.get('ID_equipement', '')
    if equip_id and isinstance(equip_id, str):
        equipment_dict[equip_id] = {
            'nom': row.get('Nom', 'nom inconnu'),
            'type': row.get('Type_de_l__quipement', 'équipement'),
            'adresse': row.get('Adresse', 'Adresse inconnue'),
            'batiment': row.get('B_timent', 'bâtiment inconnu'),
            'niveau': str(row.get('Niveau', 'niveau inconnu')) if pd.notna(row.get('Niveau', '')) else 'niveau inconnu',
            'type intervention': row.get('Type_d_intervention','intervention inconnu'),
            'reference_constructeur': row.get('Reference_constructeur','reference constructeur inconnu'),
            'date_limite': row.get('Date_limite','date limite inconnu'),
            'date_installation': row.get('Date_installation','date installation inconnu'),
            'Secteur': row.get('Secteur','secteur inconnu'),
            'Notes': row.get('Notes','notes inconnu'),
            'Mainteneur': row.get('Mainteneur','mainteneur inconnu'),
            'Commentaires du mainteneur': row.get('Commentaires','commentaires inconnus'),
            'Points de contact': row.get('Points_de_contact','points de contact inconnus'),
        }
    if equip_nom and isinstance(equip_nom, str):
        equipment_dict[equip_nom] = {
            'nom': row.get('Nom', 'nom inconnu'),
            'type': row.get('Type_de_l__quipement', 'équipement'),
            'adresse': row.get('Adresse', 'Adresse inconnue'),
            'batiment': row.get('B_timent', 'bâtiment inconnu'),
            'niveau': str(row.get('Niveau', 'niveau inconnu')) if pd.notna(row.get('Niveau', '')) else 'niveau inconnu',
            'type intervention': row.get('Type_d_intervention','intervention inconnu'),
            'reference_constructeur': row.get('Reference_constructeur','reference constructeur inconnu'),
            'date_limite': row.get('Date_limite','date limite inconnu'),
            'date_installation': row.get('Date_installation','date installation inconnu'),
            'Secteur': row.get('Secteur','secteur inconnu'),
            'Notes': row.get('Notes','notes inconnu'),
            'Mainteneur': row.get('Mainteneur','mainteneur inconnu'),
            'Commentaires du mainteneur': row.get('Commentaires','commentaires inconnus'),
            'Points de contact': row.get('Points_de_contact','points de contact inconnus'),    
        }
    

# Convertir en JSON pour l'insérer dans le prompt (limiter la taille)
equipment_json = json.dumps(equipment_dict, ensure_ascii=False)

# 📌 Fonction pour extraire un ID équipement d'une phrase
def extract_equipment_id(text):
    """
    Recherche un ID équipement dans une phrase en supposant que les ID
    sont des combinaisons de lettres et chiffres (ex: X45, 2F 120).
    """
    pattern = r"\b[A-Z0-9]+(?:\s[A-Z0-9]+)*\b"  # Capte des ID comme "X45" ou "2F 120"
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    # Vérifier si l'un des résultats correspond à un équipement existant
    for match in matches:
        if match in data_df['ID_equipement'].values:
            return match  # Retourne l'ID valide trouvé
        if match in data_df['Nom'].values:
            return match
    return None

# 📌 Fonction pour récupérer les infos d'un équipement
def get_equipment_info(equipment_id):
    row = data_df.loc[data_df['ID_equipement'] == equipment_id]
    if row.empty:
        return None

    # Récupération des infos
    adresse = row['Adresse'].values[0] if 'Adresse' in row else "Adresse inconnue"
    batiment = row['B_timent'].values[0] if 'B_timent' in row else "bâtiment inconnu"
    niveau = row['Niveau'].values[0] if 'Niveau' in row and pd.notna(row['Niveau'].values[0]) else "un niveau inconnu"
    type_equipement = row['Type_de_l__quipement'].values[0] if 'Type_de_l__quipement' in row else "équipement"
    type_intervention = row['Type_d_intervention'].values[0] if 'Type_d_intervention' in row else "intervention"

    # Construire une réponse naturelle
    response = f"Vous pouvez retrouver {type_equipement.lower()} {equipment_id} à l'adresse {adresse} au {niveau}, {batiment}."
    return response

# 📌 Route principale : affiche la page web du chatbot
@app.route("/")
def home():
    return render_template("index.html")

# 📌 API pour les requêtes du chatbot
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "Merci de fournir une question."}), 400

    # Extraire un ID équipement de la question
    # equip_id = extract_equipment_id(user_message)

    # if equip_id:
    #     response_text = get_equipment_info(equip_id)
    #     if response_text:
    #         return jsonify({"response": response_text})
    #     else:
    #         return jsonify({"response": "Désolé, je n'ai pas trouvé d'équipement correspondant à cet ID."})

    # Construction du prompt système avec le dictionnaire d'équipements
    system_prompt = f"""
    Tu es un assistant spécialisé dans la localisation d'équipements dans un bâtiment. Tu as accès à une base de données contenant des informations sur les équipements, notamment leur ID, leur type, leur adresse, leur bâtiment et leur niveau. Ton rôle est d'aider les utilisateurs à localiser un équipement en répondant à leurs questions de manière claire et concise.

    ### Base de données d'équipements (format JSON) :
    ```json
    {equipment_json}
    ```

    ### Structure de la base de données :
    Chaque entrée du dictionnaire est structurée comme suit :
    - **ID_equipement** : L'identifiant unique de l'équipement (exemple : "2F 123").
    - **type** : Le type d'équipement (exemple : "plieuse buanderie").
    - **adresse** : L'adresse exacte où se trouve l'équipement.
    - **batiment** : Le bâtiment où se trouve l'équipement.
    - **niveau** : Le niveau ou étage où se trouve l'équipement.

    ### Instructions :
    1. Si l'utilisateur demande des informations sur un équipement spécifique, utilise le dictionnaire ci-dessus pour lui fournir les informations. 
       Format de réponse : "Vous pouvez retrouver [type] [ID] à l'adresse [adresse], au [niveau], [batiment]."

    2. Si l'ID d'équipement n'est pas dans le dictionnaire, réponds : "Désolé, je n'ai pas trouvé d'équipement correspondant à cet ID."

    3. Si la question de l'utilisateur ne mentionne pas d'équipement spécifique ou n'est pas claire, demande-lui de préciser sa question et mentionne qu'il peut rechercher par ID (par exemple, "2F 123").

    4. Pour les questions générales sur le système, réponds de manière informative et utile en fonction de tes connaissances.

    5. Si l'utilisateur semble chercher un équipement sans connaître son ID, essaie de l'aider en suggérant de chercher par type ou par emplacement.
    """

    # Si aucun ID équipement n'est trouvé, utiliser Mistral avec le dictionnaire intégré
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {"role": "user", "content": user_message},
    ]

    chat_response = client.chat.complete(
        model=model,
        messages=messages,
    )

    return jsonify({"response": chat_response.choices[0].message.content})

if __name__ == "__main__":
    app.run(debug=True)