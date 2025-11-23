import streamlit as st
import pandas as pd
import gspread # Neue Bibliothek für Google Sheets
import os

# --- VORBEREITUNG & KONFIGURATION ---

# NEU: Mapping der Farben für Highlighting
COLOR_MAP = {
    'Grün': '#008000',
    'Gelb': '#FFD700',
    'Rot': '#FF4500',
    'Kein': 'transparent'
}
COLOR_OPTIONS = list(COLOR_MAP.keys())

# --- NEU: DATENBANK-FUNKTIONEN (Google Sheets) ---

@st.cache_resource(ttl=3600) # Speichert die Verbindung für 1 Stunde
def get_gsheets_connection():
    """Stellt die Verbindung zur Google Sheet Datenbank her."""
    try:
        # Versucht, die Verbindung über Streamlit's Secrets herzustellen
        # WICHTIG: Funktioniert nur, wenn st.secrets richtig konfiguriert ist (Cloud/Lokal)
        gc = gspread.service_account_from_dict(st.secrets["gsheets"])
        spreadsheet = gc.open_by_key(st.secrets["gsheets"]["spreadsheet_id"])
        return spreadsheet.worksheet("Tabelle1") 
    except Exception as e:
        # Hier wird der Fehler geworfen, wenn die App lokal ohne secrets.toml gestartet wird
        st.error(f"⚠️ Datenbankfehler: Konnte keine Verbindung zu Google Sheets herstellen. Bitte die Datei 'secrets.toml' prüfen. ({e})")
        return None

# NEU: Lädt ALLE Daten aus GSheets und filtert nach dem aktuellen Nutzer
def load_data(user_id):
    worksheet = get_gsheets_connection()
    if worksheet is None:
        # Gibt leeren DataFrame zurück, wenn keine Verbindung besteht
        return pd.DataFrame(columns=["User_ID", "Name", "Kategorie", "Stückzahl", "NEM_pro_Stück", "Bild_Pfad", "Highlight"])

    try:
        # Lädt alle Zeilen als Liste von Dictionaries
        data = worksheet.get_all_records()
        df_all = pd.DataFrame(data)

        # Stellt sicher, dass alle notwendigen Spalten existieren
        required_cols = ["User_ID", "Name", "Kategorie", "Stückzahl", "NEM_pro_Stück", "Bild_Pfad", "Highlight"]
        for col in required_cols:
            if col not in df_all.columns:
                df_all[col] = pd.NA
        
        # Datentyp-Konvertierung und Filtern
        df_all['Stückzahl'] = pd.to_numeric(df_all['Stückzahl'], errors='coerce').fillna(0).astype(int)
        df_all['NEM_pro_Stück'] = pd.to_numeric(df_all['NEM_pro_Stück'], errors='coerce').fillna(0.0)

        # Filtern nach dem aktuellen Benutzer
        df_filtered = df_all[df_all['User_ID'] == user_id].copy()
        return df_filtered
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten aus Google Sheets: {e}")
        return pd.DataFrame(columns=["User_ID", "Name", "Kategorie", "Stückzahl", "NEM_pro_Stück", "Bild_Pfad", "Highlight"])

# NEU: Speichert die Änderungen des Benutzers im Gesamt-Sheet
def save_data(df_user):
    worksheet = get_gsheets_connection()
    if worksheet is None:
        return

    try:
        # 1. Alle Daten aus GSheets holen (muss ungefiltert sein)
        df_all = pd.DataFrame(worksheet.get_all_records())
        
        # 2. Alte Einträge des aktuellen Nutzers entfernen
        df_rest = df_all[df_all['User_ID'] != st.session_state["current_user"]].copy()

        # 3. Neue und geänderte Daten des Nutzers hinzufügen
        # Fügt die User_ID zur Nutzerdatenbank hinzu, falls dies eine neue Zeile ist
        df_user['User_ID'] = st.session_state["current_user"]
        
        df_neu_gesamt = pd.concat([df_rest, df_user], ignore_index=True)

        # 4. Sheet leeren und neue Daten schreiben (ACHTUNG: dies überschreibt das gesamte Sheet)
        worksheet.clear()
        worksheet.update([df_neu_gesamt.columns.values.tolist()] + df_neu_gesamt.values.tolist())
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern in Google Sheets: {e}")
        return False


# --- HAUPTPROGRAMM ---
st.set_page_config(page_title="Feuerwerk Inventar", layout="wide", page_icon="🎆")


# --- NEU: LOGIN-LOGIK ---

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

if st.session_state["current_user"] is None:
    st.title("🎆 Feuerwerk Inventar – Cloud Login")
    st.info("Geben Sie Ihren gewünschten Benutzernamen ein. Dieser Name isoliert Ihre Daten von anderen Nutzern.")
    
    user_input = st.text_input("Benutzername (z.B. MeinVorname)", key="login_input")
    
    if st.button("App starten"):
        if user_input:
            st.session_state["current_user"] = user_input
            st.rerun()
        else:
            st.error("Bitte einen Benutzernamen eingeben.")

else:
    # --- APP WIRD AUSGEFÜHRT ---
    
    # 1. Sidebar für Info und Logout
    st.sidebar.markdown(f"### Angemeldet als: **{st.session_state['current_user']}**")
    st.sidebar.caption("Ihre Daten sind isoliert.")
    if st.sidebar.button("Logout"):
        st.session_state["current_user"] = None
        st.cache_resource.clear() # Cache löschen, um neue Verbindung zu erzwingen
        st.rerun()
    st.sidebar.markdown("---")
    
    # Daten laden
    df = load_data(st.session_state["current_user"])

    # --- SIDEBAR (LINKS) - Neuen Artikel anlegen ---
    st.sidebar.header("Neuen Artikel anlegen")

    with st.sidebar.form("add_form", clear_on_submit=True):
        neuer_name = st.text_input("Name des Artikels")
        neue_kat = st.selectbox("Kategorie", ["Batterie", "Verbund", "Raketen", "Single Shot", "Leuchtfeuerwerk", "Böller", "Sonstiges"])
        neue_anzahl = st.number_input("Stückzahl", min_value=0, value=1)
        neue_nem = st.number_input("NEM pro Stück (g)", min_value=0.0, format="%.2f")
        
        # HINWEIS: Bild-Upload entfernt, da es in der Cloud nicht direkt funktioniert!
        st.caption("Bild-Upload wurde für Cloud-Speicherung entfernt.")
        
        neues_highlight = st.selectbox("Highlight-Farbe", COLOR_OPTIONS)
        
        submit = st.form_submit_button("Artikel speichern")

        if submit and neuer_name:
            new_entry = pd.DataFrame({
                "User_ID": [st.session_state["current_user"]], # Muss hier explizit gesetzt werden
                "Name": [neuer_name], 
                "Kategorie": [neue_kat], 
                "Stückzahl": [neue_anzahl],
                "NEM_pro_Stück": [neue_nem],
                "Bild_Pfad": [pd.NA], # Auf NA setzen, da Upload entfernt
                "Highlight": [neues_highlight]
            })
            df = pd.concat([df, new_entry], ignore_index=True)
            if save_data(df):
                st.sidebar.success(f"{neuer_name} hinzugefügt und gespeichert!")
                st.rerun()
            else:
                st.sidebar.error("Speichern fehlgeschlagen.")

    # --- HAUPTBEREICH (RECHTS) ---
    tab1, tab2 = st.tabs(["Inventar & Übersicht", "Prospekte & Dokumente"])

    with tab1:
        st.title(f"Feuerwerk Inventar ({st.session_state['current_user']})")
        
        # Statistik
        col1, col2 = st.columns(2)
        total_items = df['Stückzahl'].sum()
        total_nem = (df['Stückzahl'] * df['NEM_pro_Stück']).sum() / 1000 

        col1.metric("Gesamt Artikel", f"{total_items} Stück")
        col2.metric("Gesamt NEM", f"{total_nem:.2f} kg")

        st.markdown("---")

        # Ansicht
        view_mode = st.radio("Ansicht wählen:", ["Tabelle bearbeiten", "Galerie-Ansicht"], horizontal=True)

        if view_mode == "Tabelle bearbeiten":
            st.info("Klicke in die Zellen, um Bestände oder Highlights zu ändern. Änderungen speichern sofort beim Speichern der App!")
            
            edited_df = st.data_editor(
                df, 
                column_config={
                    "Stückzahl": st.column_config.NumberColumn("Bestand", min_value=0, step=1),
                    "NEM_pro_Stück": st.column_config.NumberColumn("NEM (g)", format="%.2f g"),
                    "Highlight": st.column_config.SelectboxColumn("Highlight", options=COLOR_OPTIONS, required=True),
                },
                column_order=("Name", "Kategorie", "Stückzahl", "NEM_pro_Stück", "Highlight"), # User_ID nicht anzeigen
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )

            def highlight_text(s):
                if s == 'Grün':
                    return 'color: white; background-color: #008000'
                elif s == 'Gelb':
                    return 'color: black; background-color: #FFD700'
                elif s == 'Rot':
                    return 'color: white; background-color: #FF4500'
                return ''

            st.subheader("Farbliche Übersicht (Schreibgeschützt)")
            st.dataframe(
                edited_df.style.apply(
                    lambda x: [highlight_text(val) if x.name == 'Highlight' else '' for val in x],
                    axis=1
                ), 
                use_container_width=True, 
                hide_index=True
            )

            if not edited_df.equals(df):
                if save_data(edited_df):
                    st.toast("Daten gespeichert!")
                    st.rerun()
                else:
                    st.error("Speichern fehlgeschlagen.")
        else:
            # Galerie Ansicht (VEREINFACHT: Bilder entfernt)
            st.subheader("Übersicht")
            filter_kat = st.multiselect("Kategorie filtern", df["Kategorie"].unique())
            df_show = df if not filter_kat else df[df["Kategorie"].isin(filter_kat)]
            
            cols = st.columns(3) 
            for index, row in df_show.iterrows():
                highlight_color = COLOR_MAP.get(row.get('Highlight', 'Kein'), 'transparent')
                
                with cols[index % 3]:
                    st.markdown(
                        f"""
                        <div style="border: 3px solid {highlight_color}; border-radius: 5px; padding: 10px; margin-bottom: 15px; background-color: rgba(255, 255, 255, 0.05);">
                        """, unsafe_allow_html=True
                    )
                    
                    st.write("🖼️ Kein Bild (Cloud-Version)")
                    st.markdown(f"**{row['Name']}**")
                    st.caption(f"{row['Kategorie']} | NEM: {row['NEM_pro_Stück']}g")
                    
                    # Buttons zur Mengensteuerung
                    c1, c2, c3 = st.columns([1,1,2])
                    if c1.button("➖", key=f"minus_{index}"):
                        if df.at[index, "Stückzahl"] > 0:
                            df.at[index, "Stückzahl"] -= 1
                            save_data(df)
                            st.rerun()
                    
                    if c2.button("➕", key=f"plus_{index}"):
                        df.at[index, "Stückzahl"] += 1
                        save_data(df)
                        st.rerun()
                    
                    c3.markdown(f"### {row['Stückzahl']} Stk.")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
    with tab2:
        st.header("Prospekte & Dokumente")
        st.info("⚠️ Diese Funktion wurde entfernt, da sie lokale Dateispeicher benötigt. Für eine Cloud-Version müsste ein Dienst wie Google Drive oder S3 angebunden werden.")