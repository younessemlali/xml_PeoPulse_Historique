import streamlit as st
import xml.etree.ElementTree as ET
import re
from io import StringIO, BytesIO
import zipfile
import pandas as pd

def parse_xml_safely(content):
    """Parse XML content with proper encoding handling"""
    try:
        # Try to parse directly
        return ET.fromstring(content)
    except ET.ParseError:
        # If fails, try with encoding declaration
        if not content.startswith('<?xml'):
            content = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + content
        return ET.fromstring(content)

def find_contracts_simple(content):
    """Find all contracts by looking for CONO_TXT values and checking if HISTORIQUE exists"""
    contracts = []
    
    # Utiliser regex pour trouver les patterns
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if '<CONO_TXT>' in line and '</CONO_TXT>' in line:
            # Extraire le numéro de contrat
            match = re.search(r'<CONO_TXT>(.*?)</CONO_TXT>', line)
            if match:
                contract_num = match.group(1).strip()
                
                # Chercher si HISTORIQUE existe après STATUT_SALARIE pour ce contrat
                has_historique = False
                
                # Chercher en arrière pour trouver le début du contrat
                # puis chercher STATUT_SALARIE et HISTORIQUE
                for j in range(i, min(i + 50, len(lines))):  # Regarder les 50 lignes suivantes
                    if '<STATUT_SALARIE>' in lines[j]:
                        # Vérifier si la ligne suivante contient HISTORIQUE
                        if j + 1 < len(lines) and '<HISTORIQUE>' in lines[j + 1]:
                            has_historique = True
                        break
                
                contracts.append({
                    'numero': contract_num,
                    'line_index': i,
                    'has_historique': has_historique
                })
    
    return contracts

def add_historique_to_content(content, contracts_to_modify):
    """Add HISTORIQUE tag after STATUT_SALARIE for selected contracts"""
    if not contracts_to_modify:
        return content
    
    lines = content.split('\n')
    new_lines = []
    modified_contracts = []
    
    i = 0
    while i < len(lines):
        new_lines.append(lines[i])
        
        # Si on trouve STATUT_SALARIE
        if '<STATUT_SALARIE>' in lines[i] and '</STATUT_SALARIE>' in lines[i]:
            # Vérifier si on est dans un contrat à modifier
            # Chercher le CONO_TXT précédent pour identifier le contrat
            contract_num = None
            for j in range(max(0, i-50), i):  # Regarder jusqu'à 50 lignes avant
                if '<CONO_TXT>' in lines[j]:
                    match = re.search(r'<CONO_TXT>(.*?)</CONO_TXT>', lines[j])
                    if match:
                        contract_num = match.group(1).strip()
                        break
            
            # Si c'est un contrat à modifier et qu'il n'y a pas déjà HISTORIQUE
            if contract_num and contract_num in contracts_to_modify:
                next_line_has_historique = False
                if i + 1 < len(lines):
                    next_line_has_historique = '<HISTORIQUE>' in lines[i + 1]
                
                if not next_line_has_historique:
                    # Ajouter HISTORIQUE avec la même indentation
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    new_lines.append(' ' * indent + '<HISTORIQUE>1</HISTORIQUE>')
                    modified_contracts.append(contract_num)
        
        i += 1
    
    return '\n'.join(new_lines), modified_contracts

def main():
    st.set_page_config(
        page_title="Ajout balise HISTORIQUE - PeoPulse",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("🔧 Ajout automatique de balise HISTORIQUE")
    st.markdown("### Pour les contrats de travail PeoPulse")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Chargez vos fichiers XML",
        type=['xml'],
        accept_multiple_files=True,
        help="Vous pouvez sélectionner plusieurs fichiers XML à la fois"
    )
    
    if uploaded_files:
        st.markdown("---")
        
        # Process each file
        all_files_data = []
        
        for uploaded_file in uploaded_files:
            # Try ISO-8859-1 first (as specified by user), then other encodings
            content = None
            encodings_to_try = ['iso-8859-1', 'latin-1', 'cp1252', 'utf-8', 'utf-16']
            
            for encoding in encodings_to_try:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    content = uploaded_file.read().decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                st.error(f"❌ Impossible de lire le fichier {uploaded_file.name}. Encodage non reconnu.")
                continue
            
            try:
                # Trouver les contrats
                contracts = find_contracts_simple(content)
                
                file_data = {
                    'filename': uploaded_file.name,
                    'content': content,
                    'contracts': contracts
                }
                all_files_data.append(file_data)
            except Exception as e:
                st.error(f"❌ Erreur lors du parsing de {uploaded_file.name}: {str(e)}")
        
        if not all_files_data:
            return
            
        # Display summary
        st.subheader("📊 Résumé des fichiers chargés")
        
        total_contracts = 0
        total_needing_historique = 0
        
        for file_data in all_files_data:
            with st.expander(f"📄 {file_data['filename']}", expanded=True):
                contracts = file_data['contracts']
                
                if contracts:
                    # Create dataframe for display
                    df_data = []
                    for contract in contracts:
                        df_data.append({
                            'Numéro de contrat': contract['numero'],
                            'Balise HISTORIQUE': '✅ Présente' if contract['has_historique'] else '❌ Absente',
                            'Action': '✅ Aucune' if contract['has_historique'] else '⚠️ Ajout nécessaire'
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Count contracts
                    needs_modification = [c for c in contracts if not c['has_historique']]
                    total_contracts += len(contracts)
                    total_needing_historique += len(needs_modification)
                    
                    if needs_modification:
                        st.info(f"📝 {len(needs_modification)} contrat(s) sur {len(contracts)} nécessitent l'ajout de la balise HISTORIQUE")
                    else:
                        st.success("✅ Tous les contrats ont déjà la balise HISTORIQUE")
                else:
                    st.warning("⚠️ Aucun contrat trouvé dans ce fichier")
        
        if total_needing_historique == 0:
            st.success("✅ Tous les contrats ont déjà la balise HISTORIQUE !")
            return
            
        st.markdown("---")
        
        # Processing options
        st.subheader("🛠️ Options de traitement")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            process_mode = st.radio(
                "Mode de traitement",
                ["Traiter tous les contrats d'un coup", "Sélectionner les contrats à traiter"],
                help="Choisissez comment vous voulez traiter les contrats"
            )
        
        with col2:
            st.info("💡 La balise HISTORIQUE sera ajoutée entre STATUT_SALARIE et CONTDET_1")
        
        # Contract selection if needed
        selected_contracts = []
        
        if process_mode == "Sélectionner les contrats à traiter":
            st.subheader("📋 Sélection des contrats")
            st.markdown("Cochez les contrats que vous souhaitez modifier :")
            
            # Créer des colonnes pour un meilleur affichage
            cols = st.columns(3)
            col_index = 0
            
            for file_data in all_files_data:
                contracts_to_modify = [c for c in file_data['contracts'] if not c['has_historique']]
                
                if contracts_to_modify:
                    with cols[col_index % 3]:
                        st.markdown(f"**{file_data['filename']}**")
                        for contract in contracts_to_modify:
                            if st.checkbox(
                                f"{contract['numero']}", 
                                key=f"{file_data['filename']}_{contract['numero']}",
                                value=True  # Coché par défaut
                            ):
                                selected_contracts.append(contract['numero'])
                    col_index += 1
            
            if not selected_contracts:
                st.warning("⚠️ Veuillez sélectionner au moins un contrat à modifier")
        else:
            # Mode "tous les contrats" - sélectionner automatiquement tous les contrats sans HISTORIQUE
            for file_data in all_files_data:
                for contract in file_data['contracts']:
                    if not contract['has_historique']:
                        selected_contracts.append(contract['numero'])
        
        # Process button
        if st.button("🚀 Traiter les fichiers", type="primary", disabled=len(selected_contracts) == 0):
            with st.spinner("Traitement en cours..."):
                processed_files = []
                total_modified = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, file_data in enumerate(all_files_data):
                    status_text.text(f"Traitement de {file_data['filename']}...")
                    
                    try:
                        # Modifier le contenu
                        processed_content, modified_contracts = add_historique_to_content(
                            file_data['content'],
                            selected_contracts
                        )
                        
                        processed_files.append({
                            'filename': file_data['filename'],
                            'content': processed_content,
                            'modified_count': len(modified_contracts),
                            'modified_contracts': modified_contracts
                        })
                        
                        total_modified += len(modified_contracts)
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors du traitement de {file_data['filename']}: {str(e)}")
                    
                    progress_bar.progress((idx + 1) / len(all_files_data))
                
                progress_bar.empty()
                status_text.empty()
                
                if processed_files:
                    st.success(f"✅ Traitement terminé ! {total_modified} contrat(s) modifié(s)")
                    
                    # Results summary
                    if total_modified > 0:
                        st.subheader("📊 Résumé des modifications")
                        for pf in processed_files:
                            if pf['modified_count'] > 0:
                                with st.expander(f"✅ {pf['filename']} - {pf['modified_count']} modification(s)"):
                                    st.write("**Contrats modifiés :**")
                                    for i, contract in enumerate(pf['modified_contracts'], 1):
                                        st.write(f"{i}. {contract}")
                    
                    # Download options
                    st.subheader("💾 Téléchargement des fichiers traités")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Individual file downloads
                        st.write("**📄 Télécharger individuellement :**")
                        for pf in processed_files:
                            st.download_button(
                                label=f"💾 {pf['filename']}",
                                data=pf['content'].encode('iso-8859-1'),
                                file_name=f"modified_{pf['filename']}",
                                mime="application/xml"
                            )
                    
                    with col2:
                        # ZIP download for all files
                        if len(processed_files) > 1:
                            st.write("**📦 Télécharger en groupe :**")
                            
                            # Create ZIP file
                            zip_buffer = BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for pf in processed_files:
                                    zip_file.writestr(
                                        f"modified_{pf['filename']}",
                                        pf['content'].encode('iso-8859-1')
                                    )
                            
                            st.download_button(
                                label="📦 Télécharger tous les fichiers (ZIP)",
                                data=zip_buffer.getvalue(),
                                file_name="contrats_modifies.zip",
                                mime="application/zip"
                            )
    
    else:
        # Instructions
        st.info("""
        📌 **Instructions d'utilisation :**
        
        1. **Chargez** un ou plusieurs fichiers XML contenant vos contrats de travail
        2. L'application **analysera** automatiquement les contrats via la balise `<CONO_TXT>`
        3. **Choisissez** de traiter tous les contrats ou sélectionnez ceux à modifier
        4. **Téléchargez** les fichiers corrigés avec la balise HISTORIQUE ajoutée
        
        La balise `<HISTORIQUE>1</HISTORIQUE>` sera ajoutée automatiquement après 
        `<STATUT_SALARIE>` et avant `<CONTDET_1>` pour chaque contrat sélectionné.
        """)
        
        # Example
        with st.expander("📋 Voir un exemple de structure"):
            st.code("""
<STATUT_SALARIE>0</STATUT_SALARIE>
<HISTORIQUE>1</HISTORIQUE>
<CONTDET_1>
    <DATE>20140505</DATE>
    <RUCODE>1100</RUCODE>
    ...
</CONTDET_1>
            """, language="xml")

if __name__ == "__main__":
    main()
