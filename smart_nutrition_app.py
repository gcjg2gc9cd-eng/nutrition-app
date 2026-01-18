import streamlit as st
import math

# =========================
#  DATABASE ALIMENTI & TEMPLATE PASTI
# =========================

# Valori nutrizionali indicativi per 100 g (o per unità indicata)
# Sono stime semplificate per uso pratico, non valori da etichetta al milligrammo.
FOODS_DB = {
    "fiocchi di avena":        {"cho": 60, "pro": 13, "fat": 7},
    "farina di avena":         {"cho": 60, "pro": 13, "fat": 7},
    "banana":                  {"cho": 23, "pro": 1,  "fat": 0},
    "kiwi":                    {"cho": 15, "pro": 1,  "fat": 0.5},
    "mandorle":                {"cho": 22, "pro": 21, "fat": 50},
    "albume":                  {"cho": 1,  "pro": 11, "fat": 0},
    "riso basmati cotto":      {"cho": 28, "pro": 3,  "fat": 0.3},
    "pasta integrale cotta":   {"cho": 25, "pro": 5,  "fat": 1.5},
    "yogurt greco magro":        {"cho": 4,  "pro": 10, "fat": 0},
    "petto di pollo":          {"cho": 0,  "pro": 31, "fat": 3},
    "fesa di tacchino":        {"cho": 0,  "pro": 29, "fat": 2},
    "merluzzo":                {"cho": 0,  "pro": 18, "fat": 0.8},
    "uova intere":             {"cho": 1,  "pro": 13, "fat": 11},  # valori per 100 g (~2 uova medie)
    "passata di pomodoro":     {"cho": 5,  "pro": 1.5,"fat": 0.5},
    "tonno in scatola sgocciolato": {"cho": 0, "pro": 25, "fat": 8},
    "patate dolci cotte":      {"cho": 20, "pro": 2,  "fat": 0.1},
    "finocchi":                {"cho": 3,  "pro": 1,  "fat": 0},
    "radicchio rosso":         {"cho": 3,  "pro": 1,  "fat": 0},
    "minestrone leggerezza":   {"cho": 5,  "pro": 2,  "fat": 0.5},
    "olio extravergine di oliva": {"cho": 0, "pro": 0, "fat": 100},
    "miele":                   {"cho": 82, "pro": 0,  "fat": 0},
    "marmellata":              {"cho": 60, "pro": 0,  "fat": 0},
    "whey proteine":           {"cho": 6,  "pro": 80, "fat": 6},   # per 100 g di polvere
    "legumi cotti":            {"cho": 16, "pro": 8,  "fat": 1.5}, # media ceci/fagioli/lenticchie
    "ricotta senza lattosio":  {"cho": 3,  "pro": 9,  "fat": 10},
    "fiocchi di latte":        {"cho": 3,  "pro": 13, "fat": 4},
    "parmigiano grattugiato":  {"cho": 0,  "pro": 35, "fat": 28},
    "latte senza lattosio":    {"cho": 5,  "pro": 3.5,"fat": 1.5},
    "gallette di riso":        {"cho": 80, "pro": 7,  "fat": 2},
}

# Template di base per tipo di pasto
# Ogni template è una lista di alimenti del FOODS_DB.
MEAL_TEMPLATES = {
    "colazione": ["fiocchi di avena", "yogurt greco magro", "banana", "mandorle"],
    "spuntino": ["gallette di riso", "whey proteine", "mandorle"],
    "post-allenamento": ["riso basmati cotto", "petto di pollo", "passata di pomodoro"],
    "pranzo": ["riso basmati cotto", "petto di pollo", "olio extravergine di oliva", "finocchi"],
    "cena": ["pasta integrale cotta", "tonno in scatola sgocciolato", "olio extravergine di oliva", "radicchio rosso"],
}

# =========================
#  FUNZIONI DI SUPPORTO
# =========================

def calculate_bmr(weight, height, age, sex):
    """
    Calcolo BMR con Mifflin-St Jeor.
    weight in kg, height in cm, age in anni
    """
    if sex == "Maschio":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # Femmina
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    return bmr

def activity_factor(level):
    """
    Fattore di attività quotidiana NON sportiva.
    """
    mapping = {
        "Basso (sedentario)": 1.2,
        "Medio": 1.4,
        "Alto (molto attivo)": 1.6,
    }
    return mapping.get(level, 1.4)

def training_energy_cost(weight, duration_hours, training_type):
    """
    Stima molto semplificata del costo energetico dell'allenamento.
   # Qui usiamo MET grezzi per tipo di attività, moltiplicati per peso e durata.
    1 MET ~ 1 kcal/kg/h
    """
    # Valori indicativi, puoi affinarli
    met_map = {
        "Nessun allenamento / Riposo": 0.0,
        "Z2 / Endurance moderato": 7.0,   # es. corsa/bici moderata
        "HIIT / Intervalli": 9.0,         # intensità più alta
        "Forza": 6.0,                     # sala pesi
        "Lungo / Gara / Uscita chiave": 8.0,  # endurance lunga
    }
    met = met_map.get(training_type, 0.0)
    kcal = met * weight * duration_hours
    return kcal

def choose_cho_g_per_kg(training_type, session_importance, goal):
    """
    Sceglie i g/kg di CHO in base al tipo di giorno,
    importanza della seduta e obiettivo (mantenimento/dimagrimento/costruzione).
    I range sono indicativi e basati sulle linee guida classiche.
    """

    # Range base per tipo di giorno (min, max)
    base_ranges = {
        "Nessun allenamento / Riposo": (3.0, 4.0),
        "Z2 / Endurance moderato": (5.0, 6.0),
        "HIIT / Intervalli": (5.5, 7.0),
        "Forza": (5.0, 6.5),
        "Lungo / Gara / Uscita chiave": (7.0, 9.0),
    }

    low, high = base_ranges.get(training_type, (4.0, 5.0))

    # Scala in base all'importanza
    if session_importance == "Bassa":
        cho_g_per_kg = low
    elif session_importance == "Media":
        cho_g_per_kg = (low + high) / 2
    else:  # Alta / Chiave
        cho_g_per_kg = high

    # Aggiustamento in base all'obiettivo
    # Dimagrimento → abbassiamo leggermente, Costruzione → alziamo leggermente (entro range realistico)
    if goal == "Leggero dimagrimento":
        cho_g_per_kg = max(low, cho_g_per_kg - 0.3)
    elif goal == "Leggera costruzione":
        cho_g_per_kg = min(high, cho_g_per_kg + 0.3)

    return cho_g_per_kg

def choose_protein_g_per_kg(goal):
    """
    Proteine g/kg: valori per atleta endurance volume alto, >40 anni, con obiettivo di controllo peso.
    """
    if goal == "Leggera costruzione":
        return 2.0
    elif goal == "Leggero dimagrimento":
        return 1.9
    else:
        return 1.8

def choose_fat_g_per_kg(goal):
    """
    Grassi g/kg: minimo per salute + piccolo aggiustamento in base all'obiettivo.
    """
    if goal == "Leggera costruzione":
        return 1.0
    elif goal == "Leggero dimagrimento":
        return 0.8
    else:
        return 0.9

def meal_pattern(training_time):
    """
    Ritorna la lista dei pasti e le percentuali di CHO_fuori allenamento
    in base all'orario principale dell'allenamento.
    Le percentuali sommano a 1.0.
    """
    if training_time in ["Mattina presto", "Metà mattina"]:
        # Allenamento mattutino
        meals = [
            ("Colazione (pre-allenamento)", 0.20),
            ("Post-allenamento", 0.25),
            ("Pranzo", 0.25),
            ("Cena", 0.20),
            ("Spuntini", 0.10),
        ]
    elif training_time == "Pausa pranzo":
        meals = [
            ("Colazione", 0.20),
            ("Pranzo (pre o post)", 0.25),
            ("Spuntino pomeriggio", 0.15),
            ("Cena", 0.30),
            ("Spuntini", 0.10),
        ]
    elif training_time in ["Pomeriggio", "Sera"]:
        # Allenamento pomeridiano/serale
        meals = [
            ("Colazione", 0.15),
            ("Pranzo", 0.25),
            ("Spuntino pre-allenamento", 0.20),
            ("Cena / Post-allenamento", 0.30),
            ("Spuntini", 0.10),
        ]
    else:
        # Nessun allenamento o orario non specificato → distribuzione più uniforme
        meals = [
            ("Colazione", 0.25),
            ("Pranzo", 0.30),
            ("Cena", 0.30),
            ("Spuntini", 0.15),
        ]
    return meals

def meal_times_suggestion(training_time):
    """
    Suggerisce orari indicativi per i pasti in base all'orario principale dell'allenamento.
    Ritorna un dizionario {nome_pasto: orario_stringa}.
    Gli orari sono indicativi e pensati per una routine "classica" (puoi poi personalizzarli).
    """
    if training_time in ["Mattina presto", "Metà mattina"]:
        times = {
            "Colazione (pre-allenamento)": "circa 60–90 min prima dell'allenamento (es. 5:30–6:00 se ti alleni alle 7:00)",
            "Post-allenamento": "entro 60 min dalla fine (es. 8:30–9:00)",
            "Pranzo": "12:30–13:30",
            "Cena": "19:30–21:00",
            "Spuntini": "a metà mattina/pomeriggio se serve, lontano >2 h dal sonno",
        }
    elif training_time == "Pausa pranzo":
        times = {
            "Colazione": "7:00–8:00",
            "Pranzo (pre o post)": "subito dopo l'allenamento, idealmente entro 60 min (es. 13:30–14:30)",
            "Spuntino pomeriggio": "16:00–17:00",
            "Cena": "19:30–21:00",
            "Spuntini": "eventuale spuntino serale leggero, 2–3 h prima di dormire",
        }
    elif training_time in ["Pomeriggio", "Sera"]:
        times = {
            "Colazione": "7:00–8:00",
            "Pranzo": "12:30–13:30",
            "Spuntino pre-allenamento": "60–120 min prima dell'allenamento (es. 16:30–17:00 se ti alleni alle 18:30)",
            "Cena / Post-allenamento": "entro 1–2 h dalla fine dell'allenamento (es. 20:30–21:30)",
            "Spuntini": "eventuale spuntino mattina o metà pomeriggio, a seconda della fame",
        }
    else:
        # Nessun allenamento / generico
        times = {
            "Colazione": "7:00–8:30",
            "Pranzo": "12:30–13:30",
            "Cena": "19:30–21:00",
            "Spuntini": "a metà mattina/pomeriggio se serve",
        }
    return times

def split_protein_fat_across_meals(total_pro, total_fat, meals):
    """
)
    Distribuisce proteine e grassi in modo semplice:
    - proteine: più uniformi
    - grassi: leggermente più su pasti principali (colazione/pranzo/cena)
    """
    n_meals = len(meals)
    pro_per_meal = total_pro / n_meals

    # Distribuzione grassi: pasti principali un po' più alti
    # Peso base per ogni pasto
    weights = []
    for name, _ in meals:
        if "Spuntino" in name:
            weights.append(0.5)
        else:
            weights.append(1.0)
    weight_sum = sum(weights)
    fat_per_unit = total_fat / weight_sum
    fat_allocation = [w * fat_per_unit for w in weights]

    return pro_per_meal, fat_allocation
def hydration_rate(temp_condition, sweat_rate):
    """Stima dei litri di acqua/ora in base a temperatura e sudorazione.
    Ritorna L/h."""
    # Base per sudorazione
    base_map = {
        "Bassa": 0.45,
        "Media": 0.65,
        "Alta": 0.85,
    }
    base = base_map.get(sweat_rate, 0.65)

    # Fattore temperatura
    temp_factor_map = {
        "Freddo": 0.9,
        "Temperato": 1.0,
        "Caldo": 1.15,
        "Molto caldo": 1.3,
    }
    temp_factor = temp_factor_map.get(temp_condition, 1.0)

    return base * temp_factor


def sodium_rate(sweat_rate):
    """
    Stima dei mg di sodio/ora in base alla sudorazione.
    Ritorna mg/h.
    """
    sodium_map = {
        "Bassa": 350,
        "Media": 550,
        "Alta": 800,
    }
    return sodium_map.get(sweat_rate, 550)
def classify_meal_type(meal_name, training_time):
    """
    Classifica il tipo di pasto in base al nome e all'orario allenamento,
    per scegliere il template corretto.
    """
    name_lower = meal_name.lower()
    if "colazione" in name_lower:
        return "colazione"
    if "post-allenamento" in name_lower or "Cena / Post-allenamento".lower() in name_lower:
        return "post-allenamento"
    if "spuntino" in name_lower:
        return "spuntino"
    # Pranzo/cena generici
    if "pranzo" in name_lower:
        return "pranzo"
    if "cena" in name_lower:
        return "cena"
    # fallback
    return "pranzo"


def suggest_meal(meal_name, cho_target, pro_target, fat_target, training_time):
    """
    Genera un 'piatto unico' indicativo per il pasto, usando i tuoi alimenti preferiti.
    Ritorna:
      - lista di tuple (alimento, grammi)
      - macro stimati totali (cho, pro, fat)
    """

    meal_type = classify_meal_type(meal_name, training_time)
    template_foods = MEAL_TEMPLATES.get(meal_type, MEAL_TEMPLATES["pranzo"])

    # Impostiamo porzioni base in grammi per ogni alimento nel template
    # (valori iniziali che poi scalarliamo)
    base_portions = {}
    for food in template_foods:
        if meal_type == "colazione":
            if "fiocchi di avena" in food or "farina di avena" in food:
                base_portions[food] = 50
            elif "yogurt" in food:
                base_portions[food] = 150
            elif "banana" in food or "kiwi" in food:
                base_portions[food] = 100
            elif "mandorle" in food:
                base_portions[food] = 10
            else:
                base_portions[food] = 50
        elif meal_type == "spuntino":
            if "gallette" in food:
                base_portions[food] = 20  # ~2-3 gallette
            elif "whey" in food:
                base_portions[food] = 30  # ~1 misurino
            elif "mandorle" in food:
                base_portions[food] = 10
            else:
                base_portions[food] = 50
        elif meal_type == "post-allenamento":
            if "riso basmati" in food:
                base_portions[food] = 120
            elif "petto di pollo" in food:
                base_portions[food] = 120
            elif "passata di pomodoro" in food:
                base_portions[food] = 80
            else:
                base_portions[food] = 50
        else:  # pranzo/cena
            if "riso basmati" in food or "pasta integrale" in food or "patate dolci" in food:
                base_portions[food] = 120
            elif "petto di pollo" in food or "fesa di tacchino" in food or "merluzzo" in food or "tonno" in food or "legumi" in food:
                base_portions[food] = 120
            elif "olio extravergine" in food:
                base_portions[food] = 10  # ~1 cucchiaio
            elif "parmigiano" in food:
                base_portions[food] = 10
            else:
                base_portions[food] = 80

    # Calcoliamo macro per le porzioni base
    def macros_for_portions(portions_dict):
        total_cho = total_pro = total_fat = 0
        for food, grams in portions_dict.items():
            data = FOODS_DB.get(food, None)
            if not data:
                continue
            factor = grams / 100.0
            total_cho += data["cho"] * factor
            total_pro += data["pro"] * factor
            total_fat += data["fat"] * factor
        return total_cho, total_pro, total_fat

    base_cho, base_pro, base_fat = macros_for_portions(base_portions)

    # Se i target sono molto diversi, scalare le porzioni tutte insieme
    # in base ai carboidrati (priorità), con limiti per non uscire da proporzioni ragionevoli.
    scale_factor = 1.0
    if base_cho > 0 and cho_target > 0:
        scale_factor = cho_target / base_cho

    # Limitiamo lo scaling per evitare numeri assurdi
    scale_factor = max(0.6, min(scale_factor, 1.8))

    scaled_portions = {food: grams * scale_factor for food, grams in base_portions.items()}
    final_cho, final_pro, final_fat = macros_for_portions(scaled_portions)

    return scaled_portions, (final_cho, final_pro, final_fat)

# =========================
#  INTERFACCIA STREAMLIT
# =========================

st.set_page_config(page_title="Smart Nutrition & Training Day Planner", layout="wide")

st.title("Smart Nutrition & Training Day Planner")
st.write(
    "App per pianificare i macro giornalieri e il timing dei carboidrati "
    "in base a profilo atleta, allenamento del giorno e obiettivi."
)

# -------------------------
# COLONNE PRINCIPALI
# -------------------------
col1, col2 = st.columns(2)

# -------------------------
# SEZIONE 1 – PROFILO ATLETA
# -------------------------
with col1:
    st.header("1. Profilo atleta")

    age = st.number_input("Età (anni)", min_value=10, max_value=90, value=35, step=1)
    sex = st.selectbox("Sesso", ["Maschio", "Femmina"])
    weight = st.number_input("Peso attuale (kg)", min_value=35.0, max_value=150.0, value=70.0, step=0.5)
    height = st.number_input("Altezza (cm)", min_value=140.0, max_value=210.0, value=175.0, step=1.0)

    activity_level = st.selectbox(
        "Livello di attività quotidiana (non sportiva)",
        ["Basso (sedentario)", "Medio", "Alto (molto attivo)"],
        index=1
    )

    weight_goal = st.selectbox(
        "Obiettivo di composizione corporea",
        ["Mantenimento", "Leggero dimagrimento", "Leggera costruzione"],
        index=1
    )

    bmr = calculate_bmr(weight, height, age, sex)
    act_factor = activity_factor(activity_level)
    base_tdee = bmr * act_factor

    st.markdown(f"**BMR stimato**: {bmr:.0f} kcal")
    st.markdown(f"**TDEE base (senza allenamento)**: {base_tdee:.0f} kcal")

# -------------------------
# SEZIONE 2 – ALLENAMENTO DEL GIORNO
# -------------------------
with col2:
    st.header("2. Allenamento del giorno")

    training_type = st.selectbox(
        "Tipo di allenamento",
        [
            "Nessun allenamento / Riposo",
            "Z2 / Endurance moderato",
            "HIIT / Intervalli",
            "Forza",
            "Lungo / Gara / Uscita chiave",
        ],
        index=1
    )

    session_importance = st.selectbox(
        "Importanza della seduta",
        ["Bassa", "Media", "Alta / Chiave"],
        index=1
    )

    st.subheader("Durata allenamento principale")
    duration_hours = st.number_input("Ore", min_value=0, max_value=6, value=1, step=1)
    duration_minutes = st.number_input("Minuti", min_value=0, max_value=59, value=30, step=5)
    total_duration_hours = duration_hours + duration_minutes / 60.0

    training_time = st.selectbox(
        "Orario principale dell'allenamento",
        [
            "Nessun allenamento / Non specificato",
            "Mattina presto",
            "Metà mattina",
            "Pausa pranzo",
            "Pomeriggio",
            "Sera",
        ],
        index=1 if training_type != "Nessun allenamento / Riposo" else 0
    )

    training_kcal = training_energy_cost(weight, total_duration_hours, training_type)
    st.markdown(f"**Stima costo energetico allenamento**: {training_kcal:.0f} kcal")

# -------------------------
# SEZIONE 3 – ENERGIA & MACRO TOTALI
# -------------------------
st.header("3. Obiettivo energetico e macro totali")

# TDEE del giorno = TDEE base + costo allenamento
day_tdee = base_tdee + training_kcal

# Aggiustamento in base all'obiettivo
if weight_goal == "Mantenimento":
    delta_kcal = 0
elif weight_goal == "Leggero dimagrimento":
    delta_kcal = -300  # deficit moderato
else:  # Leggera costruzione
    delta_kcal = 200   # surplus moderato

target_kcal = day_tdee + delta_kcal

st.markdown(f"**TDEE del giorno (incluso allenamento)**: {day_tdee:.0f} kcal")
st.markdown(f"**Kcal target (dopo obiettivo)**: {target_kcal:.0f} kcal")

# Proteine
pro_g_per_kg = choose_protein_g_per_kg(weight_goal)
total_pro_g = pro_g_per_kg * weight
pro_kcal = total_pro_g * 4

# Grassi
fat_g_per_kg = choose_fat_g_per_kg(weight_goal)
total_fat_g = fat_g_per_kg * weight
fat_kcal = total_fat_g * 9

# Carboidrati (da linee guida in g/kg per tipo giorno)
cho_g_per_kg = choose_cho_g_per_kg(training_type, session_importance, weight_goal)
total_cho_g = cho_g_per_kg * weight
cho_kcal = total_cho_g * 4

macro_total_kcal = pro_kcal + fat_kcal + cho_kcal

st.subheader("Macro teorici da linee guida (prima verifica kcal)")
colm1, colm2, colm3, colm4 = st.columns(4)
with colm1:
    st.markdown(f"**CHO**: {total_cho_g:.0f} g  \n({cho_g_per_kg:.1f} g/kg)")
with colm2:
    st.markdown(f"**PRO**: {total_pro_g:.0f} g  \n({pro_g_per_kg:.1f} g/kg)")
with colm3:
    st.markdown(f"**FAT**: {total_fat_g:.0f} g  \n({fat_g_per_kg:.1f} g/kg)")
with colm4:
    st.markdown(f"**Kcal da macro**: {macro_total_kcal:.0f} kcal")

# Avviso se lo scostamento kcal è grande
diff_kcal = macro_total_kcal - target_kcal
if abs(diff_kcal) > 200:
    st.warning(
        f"Attenzione: le kcal derivate dai macro ({macro_total_kcal:.0f}) "
        f"si discostano di circa {diff_kcal:.0f} kcal dal target ({target_kcal:.0f}). "
        "Puoi accettare questo margine o valutare un aggiustamento manuale."
    )

st.markdown(
    "Per semplicità in questa v1 manteniamo i macro come da linee guida, "
    "accettando un piccolo scostamento dal target calorico quando necessario."
)

# -------------------------
# SEZIONE 4 – TIMING E DISTRIBUZIONE DEI CHO
# -------------------------
st.header("4. Timing dei carboidrati e distribuzione per pasti")

if training_type == "Nessun allenamento / Riposo" or total_duration_hours <= 0:
    st.markdown(
        "Oggi non è previsto allenamento, quindi non consideriamo CHO durante l'esercizio. "
        "I CHO vengono distribuiti tra i pasti principali e gli eventuali spuntini."
    )
    cho_during_total = 0.0
else:
    st.subheader("CHO durante allenamento")
    cho_per_hour = st.slider(
        "Quanti g di CHO/ora vuoi assumere durante l'allenamento?",
        min_value=20,
        max_value=120,
        value=60,
        step=5
    )
    cho_during_total = cho_per_hour * total_duration_hours
    st.markdown(
        f"- Durata allenamento: **{total_duration_hours:.2f} h**  \n"
        f"- CHO durante: **{cho_during_total:.0f} g** "
        f"({cho_per_hour} g/h)"
    )

# CHO rimanenti da distribuire fuori allenamento
cho_outside = max(total_cho_g - cho_during_total, 0)

st.subheader("Distribuzione CHO fuori allenamento")

meals = meal_pattern(training_time if training_type != "Nessun allenamento / Riposo" else "Nessun allenamento / Non specificato")

st.markdown(f"**CHO totali giorno**: {total_cho_g:.0f} g")
st.markdown(f"**CHO durante allenamento**: {cho_during_total:.0f} g")
st.markdown(f"**CHO fuori allenamento**: {cho_outside:.0f} g")

# Distribuzione CHO per pasto
meal_rows = []
for name, perc in meals:
    cho_meal = cho_outside * perc
    meal_rows.append((name, perc, cho_meal))

# Distribuzione PRO e FAT tra i pasti
pro_per_meal, fat_allocation = split_protein_fat_across_meals(total_pro_g, total_fat_g, meals)

# Mostra tabella riassuntiva

st.subheader("Piano giornaliero per pasti")

# Orari consigliati per i pasti
meal_times = meal_times_suggestion(
    training_time if training_type != "Nessun allenamento / Riposo" else "Nessun allenamento / Non specificato"
)

st.markdown(
    "| Pasto | Orario consigliato | % CHO_fuori | CHO (g) | PRO (g) | FAT (g) |\n"
    "|-------|--------------------|------------:|--------:|--------:|--------:|\n"
)
for i, (name, perc, cho_meal) in enumerate(meal_rows):
    fat_meal = fat_allocation[i]
    time_str = meal_times.get(name, "")
    st.markdown(
        f"| {name} | {time_str} | {perc*100:.0f}% | {cho_meal:.0f} | {pro_per_meal:.0f} | {fat_meal:.0f} |"
    )

# -------------------------
# SUGGERIMENTI DI PASTI (PIATTO UNICO)
# -------------------------
st.subheader("Suggerimenti di pasti (piatto unico)")

for i, (name, perc, cho_meal) in enumerate(meal_rows):
    fat_meal = fat_allocation[i]
    pro_meal = pro_per_meal  # proteine distribuite uniformemente tra i pasti

    st.markdown(f"**{name}**")

    # Genera piatto unico per questo pasto
    portions, (m_cho, m_pro, m_fat) = suggest_meal(
        name,
        cho_meal,
        pro_meal,
        fat_meal,
        training_time
    )

    # Elenco alimenti con grammi
    lines = []
    for food, grams in portions.items():
        lines.append(f"- {grams:.0f} g di {food}")
    foods_str = "\n".join(lines)

    st.markdown(foods_str)
    st.markdown(
        f"_Macro stimati per questo pasto_: "
        f"**{m_cho:.0f} g CHO**, **{m_pro:.0f} g PRO**, **{m_fat:.0f} g FAT** "
        f"(target teorico: {cho_meal:.0f} CHO / {pro_meal:.0f} PRO / {fat_meal:.0f} FAT)"
    )
    st.markdown("---")
# -------------------------
# SEZIONE 4B – IDRATAZIONE & SALI
# -------------------------
st.header("4B. Idratazione ed elettroliti (opzionale)")

if training_type == "Nessun allenamento / Riposo" or total_duration_hours <= 0:
    st.markdown("Nessun allenamento previsto: nessuna raccomandazione specifica su idratazione/sodio.")
else:
    st.subheader("Parametri ambientali e personali")

    temp_condition = st.selectbox(
        "Condizioni di temperatura",
        ["Freddo", "Temperato", "Caldo", "Molto caldo"],
        index=1
    )

    sweat_rate = st.selectbox(
        "Quanto sudi in genere?",
        ["Bassa", "Media", "Alta"],
        index=1
    )

    l_per_hour = hydration_rate(temp_condition, sweat_rate)
    total_liters = l_per_hour * total_duration_hours

    na_mg_per_hour = sodium_rate(sweat_rate)
    total_na_mg = na_mg_per_hour * total_duration_hours

    # Traduzione pratica in borracce da 500 ml e compresse da 300 mg
    bottle_size_l = 0.5
    bottles = total_liters / bottle_size_l

    pill_na_mg = 300
    pills = total_na_mg / pill_na_mg

    st.markdown(
        f"- Durata allenamento: **{total_duration_hours:.2f} h**  \n"
        f"- Acqua consigliata: **{l_per_hour:.2f} L/h**, totale **{total_liters:.2f} L**.  \n"
        f"- Sodio consigliato: **{na_mg_per_hour:.0f} mg/h**, totale **{total_na_mg:.0f} mg**."
    )

    st.markdown(
        f"In pratica, per questa seduta equivale circa a **{bottles:.1f} borracce** da 500 ml "
        f"e **{pills:.1f} compresse** da {pill_na_mg} mg di sodio."
    )

    st.info(
        "Questi sono valori indicativi: adatta sempre idratazione e sali alle tue sensazioni, "
        "alla frequenza urinaria, al peso pre/post allenamento e a eventuali consigli medici."
    )
# -------------------------
# RIEPILOGO FINALE
# -------------------------
st.header("5. Riepilogo in linguaggio umano")

st.markdown(
    f"- Oggi: **{sex}**, {age} anni, {weight:.1f} kg, {height:.0f} cm.  \n"
    f"- Allenamento: **{training_type}**, durata **{total_duration_hours:.2f} h**, "
    f"importanza **{session_importance}**, orario **{training_time}**.  \n"
    f"- Obiettivo: **{weight_goal}**."
)

st.markdown(
    f"- Kcal target del giorno (stima): **{target_kcal:.0f} kcal**.  \n"
    f"- Macro teorici: **{total_cho_g:.0f} g CHO**, **{total_pro_g:.0f} g PRO**, "
    f"**{total_fat_g:.0f} g FAT**."
)

if cho_during_total > 0:
    st.markdown(
        f"- Durante l'allenamento: **{cho_per_hour} g/h** di CHO per **{total_duration_hours:.2f} h**, "
        f"totale **{cho_during_total:.0f} g**."
    )
else:
    st.markdown("- Nessun CHO specifico durante l'allenamento previsto oggi.")

st.markdown(
    "Il resto dei carboidrati è distribuito sui pasti in modo da privilegiare quelli a ridosso dell'allenamento, "
    "mantenendo comunque un apporto sufficiente negli altri momenti della giornata."
)

# Suggerimento/coaching
if training_type != "Nessun allenamento / Riposo" and cho_per_hour if training_type != "Nessun allenamento / Riposo" else 0 < 40:
    st.info(
        "Nota: per sedute endurance moderate o lunghe, 20–30 g/h possono essere pochi. "
        "Se percepisci cali di energia o recupero lento, valuta di provare 40–60 g/h."
    )

st.write("---")
st.caption(
    "Questa app fornisce stime generali basate su linee guida. "
    "Adatta sempre i numeri alle tue sensazioni, digestione, storia clinica e indicazioni del tuo medico/nutrizionista."
)