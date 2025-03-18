from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import requests
import re
from dotenv import load_dotenv
from datetime import datetime

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration de l'API FastAPI
app = FastAPI()

# Ajouter CORS pour permettre à Flask d'accéder à FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autoriser toutes les origines (changer en production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monter le dossier 'static' pour servir les fichiers statiques (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Charger les données du CSV
csv_file_path = 'cleaned_merged_equipment_intervention.csv'
df = pd.read_csv(csv_file_path, encoding='ISO-8859-1', delimiter=';')

# Convertir les colonnes de dates en objets datetime
date_columns = ['Date limite', 'Date de réalisation']
for col in date_columns:
    df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')

# Remplacer les valeurs NaN par une chaîne vide pour éviter les erreurs JSON
df.fillna('', inplace=True)

# Modèle de requête
class QuestionRequest(BaseModel):
    question: str

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """ Servir la page index.html """
    try:
        with open(os.path.join("templates", "index.html"), encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Page index.html non trouvée.")

@app.post("/ask")
def ask_mistral(request: QuestionRequest):
    """ Répondre à une question en utilisant l'API Mistral avec les données du CSV """
    try:
        question_lower = request.question.lower()
        print(f"Question reçue : {question_lower}")

        # Extraction de l'ID d'équipement via regex
        match = re.search(r'\bID\s*[:=\s]+\s*([\w-]+)\b', question_lower)
        if match:
            equipment_id = match.group(1).strip()
            print(f"ID d'équipement extrait : {equipment_id}")

            # Rechercher l'équipement dans le DataFrame
            equipment_info = df[df['ID equipement'] == equipment_id]

            if not equipment_info.empty:
                equipment_info = equipment_info.iloc[0]

                # Préparer les données pertinentes
                relevant_data = {
                    "Nom": equipment_info['Nom'],
                    "ID equipement": equipment_info['ID equipement'],
                    "Référence constructeur": equipment_info['Référence constructeur'],
                    "Date d'installation": str(equipment_info["Date d'installation"]),
                    "Notes": equipment_info['Notes'],
                    "Secteur": equipment_info['Secteur'],
                    "Bâtiment": equipment_info['Bâtiment'],
                    "Adresse": equipment_info['Adresse'],
                    "Niveau": equipment_info['Niveau'],
                    "Salle": equipment_info['Salle'],
                    "Date limite": str(equipment_info['Date limite']),
                    "Date de réalisation": str(equipment_info['Date de réalisation']),
                    "Type de l'équipement": equipment_info["Type d'équipement"],
                    "Type d'intervention": equipment_info["Type d'intervention"],
                    "Objet de l'intervention": equipment_info["Objet d'intervention"],
                    "Durée": equipment_info['Durée'],
                    "Mainteneur": equipment_info['Mainteneur'],
                    "Contrôleur": equipment_info['Contrôleur'],
                    "Commentaire mainteneur": equipment_info['Commentaire mainteneur'],
                    "Motif de rejet": equipment_info['Motif de rejet'],
                    "Points de contrôles": equipment_info['Points de contrôles']
                }

                # Envoyer la requête à Mistral
                headers = {
                    "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "mistral-medium",
                    "messages": [{"role": "user", "content": f"Réponds à la question : {question_lower}\nDonnées : {relevant_data}"}],
                    "temperature": 0.7
                }

                response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
                response_json = response.json()
                
                print(f"Réponse Mistral AI : {response_json}")

                if "choices" in response_json and len(response_json["choices"]) > 0:
                    return {"response": response_json["choices"][0]["message"]["content"].encode("utf-8").decode("utf-8")}
                else:
                    raise HTTPException(status_code=500, detail="Réponse invalide de Mistral AI.")
            else:
                raise HTTPException(status_code=404, detail="Aucune information pour cet ID d'équipement.")
        else:
            raise HTTPException(status_code=400, detail="ID d'équipement non trouvé dans la question.")

    except HTTPException as http_err:
        print(f"Erreur HTTP : {http_err}")
        raise http_err
    except Exception as e:
        print(f"Erreur : {e}")
        raise HTTPException(status_code=500, detail=str(e))