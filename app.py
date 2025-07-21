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
    
    # D'abord, trouver tous les CONO_TXT
    cono_positions = []
    for i, line in enumerate(lines):
        if '<CONO_TXT>' in line and '</CONO_TXT>' in line:
            match = re.search(r'<CONO_TXT>(.*?)</CONO_TXT>', line)
            if match:
                cono_positions.append({
                    'numero': match.group(1).strip(),
                    'line': i
                })
    
    # Pour chaque CONO_TXT trouvé, vérifier s'il y a HISTORIQUE après STATUT_SALARIE
    for cono in cono_positions:
        has_historique = False
        statut_line = None
        
        # Chercher STATUT_SALARIE après CONO_TXT
        for j in range(cono['line'], min(cono['line'] + 100, len(lines))):
            if '<STATUT_SALARIE>' in lines[j] and '</STATUT_SALARIE>' in lines[j]:
                statut_line = j
                # Vérifier si la ligne suivante contient HISTORIQUE
                if j + 1 < len(lines) and '<HISTORIQUE>' in lines[j + 1] and '</HISTORIQUE>' in lines[j + 1]:
                    has_historique = True
                break
        
        contracts.append({
            'numero': cono['numero'],
            'line_index': cono['line'],
            'statut_line': statut_line,
            'has_historique': has_historique
        })
    
    return contracts

def add_historique_to_content(content, contracts_to_modify):
    """Add HISTORIQUE tag after STATUT_SALARIE for selected contracts"""
    if not contracts_to_modify:
        return content, []
    
    lines = content.split('\n')
    new_lines = []
    modified_contracts = []
    current_contract = None
    
    # D'abord, créer un mapping des positions des contrats
    contract_positions = {}
    for i, line in enumerate(lines):
        if '<CONO_TXT>' in line and '</CONO_TXT>' in line:
            match = re.search(r'<CONO_TXT>(.*?)</CONO_TXT>', line)
            if match:
                contract_num = match.group(1).strip()
                contract_positions[i] = contract_num
    
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Mettre à jour le contrat courant si on trouve un CONO_TXT
        if i in contract_positions:
            current_contract = contract_positions[i]
        
        # Si on trouve STATUT_SALARIE et qu'on est dans un contrat à modifier
        if '<STATUT_SALARIE>' in line and '</STATUT_SALARIE>' in line:
            if current_contract and current_contract in contracts_to_modify:
                # Vérifier que la ligne suivante n'est pas déjà HISTORIQUE
                next_has_historique = False
                if i + 1 < len(lines):
                    next_has_historique = '<HISTORIQUE>' in lines[i + 1] and '</HISTORIQUE>' in lines[i + 1]
                
                if not next_has_historique:
                    # Ajouter HISTORIQUE avec la même indentation que STATUT_SALARIE
                    indent = len(line) - len(line.lstrip())
                    historique_line = ' ' * indent + '<HISTORIQUE>1</HISTORIQUE>'
                    new_lines.append(historique_line)
                    modified_contracts.append(current_contract)
        
        i += 1
    
    return '\n'.join(new_lines), list(set(modified_contracts))  # Enlever les doublons

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
