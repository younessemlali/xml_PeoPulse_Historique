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

def find_contracts(root):
    """Find all contracts in the XML and their details"""
    contracts = []
    
    # Stratégie : Pour chaque STATUT_SALARIE, trouver le CONO_TXT associé
    for elem in root.iter():
        if elem.tag == 'STATUT_SALARIE':
            # Trouver le parent qui contient à la fois STATUT_SALARIE et CONO_TXT
            parent = elem
            contract_elem = None
            
            # Remonter dans l'arbre pour trouver le conteneur du contrat
            levels_up = 0
            while levels_up < 10:  # Limite de sécurité
                # Chercher le parent
                potential_parent = None
                for p in root.iter():
                    if parent in list(p):
                        potential_parent = p
                        break
                
                if potential_parent is None:
                    break
                    
                # Vérifier si ce parent contient CONO_TXT
                cono_txt = potential_parent.find('.//CONO_TXT')
                if cono_txt is not None:
                    contract_elem = potential_parent
                    break
                
                parent = potential_parent
                levels_up += 1
            
            if contract_elem is not None:
                # Récupérer le numéro de contrat
                cono_elem = contract_elem.find('.//CONO_TXT')
                if cono_elem is not None and cono_elem.text:
                    contract_num = cono_elem.text.strip()
                    
                    # Vérifier si HISTORIQUE existe déjà
                    historique = None
                    # Chercher HISTORIQUE juste après STATUT_SALARIE
                    children_list = list(contract_elem)
                    for i, child in enumerate(children_list):
                        if child.tag == 'STATUT_SALARIE':
                            # Regarder l'élément suivant
                            if i + 1 < len(children_list) and children_list[i + 1].tag == 'HISTORIQUE':
                                historique = children_list[i + 1]
                            break
                    
                    # Éviter les doublons
                    already_added = any(c['numero'] == contract_num for c in contracts)
                    if not already_added:
                        contracts.append({
                            'numero': contract_num,
                            'element': contract_elem,
                            'has_historique': historique is not None,
                            'historique_value': historique.text if historique is not None else None
                        })
    
    return contracts

def add_historique_to_contract(contract_elem):
    """Add HISTORIQUE tag after STATUT_SALARIE and before CONTDET_1"""
    # Find STATUT_SALARIE position
    statut_index = None
    for i, child in enumerate(contract_elem):
        if child.tag == 'STATUT_SALARIE':
            statut_index = i
            break
    
    if statut_index is not None:
        # Create HISTORIQUE element
        historique = ET.Element('HISTORIQUE')
        historique.text = '1'
        
        # Insert after STATUT_SALARIE
        contract_elem.insert(statut_index + 1, historique)
        return True
    
    return False

def process_xml_content(content, selected_contracts=None):
    """Process XML content and add HISTORIQUE tags"""
    root = parse_xml_safely(content)
    contracts = find_contracts(root)
    
    modified_contracts = []
    
    for contract in contracts:
        if not contract['has_historique']:
            if selected_contracts is None or contract['numero'] in selected_contracts:
                if add_historique_to_contract(contract['element']):
                    modified_contracts.append(contract['numero'])
    
    # Convert back to string with proper formatting
    xml_str = ET.tostring(root, encoding='unicode')
    
    # Check if original content had XML declaration
    if content.strip().startswith('<?xml'):
        # Extract original declaration to preserve encoding
        first_line = content.split('\n')[0]
        if 'encoding=' in first_line:
            # Keep original declaration
            xml_str = first_line + '\n' + xml_str
        else:
            # Add declaration with ISO-8859-1
            xml_str = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + xml_str
    else:
        # Add declaration with ISO-8859-1
        xml_str = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + xml_str
    
    return xml_str, modified_contracts

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
                root = parse_xml_safely(content)
                contracts = find_contracts(root)
                
                file_data = {
                    'filename': uploaded_file.name,
                    'content': content,
                    'contracts': contracts
                }
                all_files_data.append(file_data)
            except Exception as e:
                st.error(f"❌ Erreur lors du parsing XML de {uploaded_file.name}: {str(e)}")
        
        # Display summary
        st.subheader("📊 Résumé des fichiers chargés")
        
        for file_data in all_files_data:
            with st.expander(f"📄 {file_data['filename']}"):
                contracts = file_data['contracts']
                
                if contracts:
                    # Debug : afficher le nombre de contrats trouvés
                    st.write(f"**Nombre de contrats trouvés:** {len(contracts)}")
                    
                    # Create dataframe for display
                    df_data = []
                    for contract in contracts:
                        df_data.append({
                            'Numéro de contrat': contract['numero'] if contract['numero'] else 'Non trouvé',
                            'Balise HISTORIQUE présente': '✅ Oui' if contract['has_historique'] else '❌ Non',
                            'Valeur actuelle': contract['historique_value'] if contract['has_historique'] else '-',
                            'Action requise': '✅ Aucune' if contract['has_historique'] else '⚠️ Ajout nécessaire'
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Count contracts needing modification
                    needs_modification = [c for c in contracts if not c['has_historique']]
                    
                    if needs_modification:
                        st.info(f"📝 {len(needs_modification)} contrat(s) nécessitent l'ajout de la balise HISTORIQUE")
                    else:
                        st.success("✅ Tous les contrats ont déjà la balise HISTORIQUE")
                else:
                    st.warning("⚠️ Aucun contrat trouvé dans ce fichier")
        
        st.markdown("---")
        
        # Processing options
        st.subheader("🛠️ Options de traitement")
        
        col1, col2 = st.columns(2)
        
        with col1:
            process_mode = st.radio(
                "Mode de traitement",
                ["Traiter tous les contrats d'un coup", "Sélectionner les contrats à traiter"],
                help="Choisissez comment vous voulez traiter les contrats"
            )
        
        with col2:
            st.info("💡 La balise HISTORIQUE sera ajoutée avec la valeur '1' après STATUT_SALARIE")
        
        # Contract selection if needed
        selected_contracts = None
        if process_mode == "Sélectionner les contrats à traiter":
            st.subheader("📋 Sélection des contrats")
            
            all_contracts_to_modify = []
            contract_mapping = {}  # Pour garder la correspondance fichier-contrat
            
            for file_data in all_files_data:
                for c in file_data['contracts']:
                    if not c['has_historique']:
                        # Afficher le numéro de contrat et le fichier source
                        display_name = f"Contrat: {c['numero']} (Fichier: {file_data['filename']})"
                        all_contracts_to_modify.append(display_name)
                        # Stocker la correspondance
                        contract_mapping[display_name] = c['numero']
            
            if all_contracts_to_modify:
                selected = st.multiselect(
                    "Sélectionnez les contrats à modifier",
                    all_contracts_to_modify,
                    default=all_contracts_to_modify,
                    help="Les numéros affichés correspondent aux valeurs dans la balise <CONO_TXT>"
                )
                
                # Extract contract numbers from selection
                selected_contracts = [contract_mapping[s] for s in selected]
            else:
                st.info("ℹ️ Aucun contrat ne nécessite de modification")
        
        # Process button
        if st.button("🚀 Traiter les fichiers", type="primary"):
            with st.spinner("Traitement en cours..."):
                processed_files = []
                total_modified = 0
                
                for file_data in all_files_data:
                    try:
                        processed_content, modified_contracts = process_xml_content(
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
                
                if processed_files:
                    st.success(f"✅ Traitement terminé ! {total_modified} contrat(s) modifié(s)")
                    
                    # Results summary
                    st.subheader("📊 Résumé des modifications")
                    for pf in processed_files:
                        if pf['modified_count'] > 0:
                            with st.expander(f"✅ {pf['filename']} - {pf['modified_count']} modification(s)"):
                                st.write("Contrats modifiés:")
                                for contract in pf['modified_contracts']:
                                    st.write(f"• {contract}")
                    
                    # Download options
                    st.subheader("💾 Téléchargement des fichiers traités")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Individual file downloads
                        st.write("**Télécharger individuellement:**")
                        for pf in processed_files:
                            st.download_button(
                                label=f"📄 {pf['filename']}",
                                data=pf['content'].encode('iso-8859-1'),
                                file_name=f"modified_{pf['filename']}",
                                mime="application/xml"
                            )
                    
                    with col2:
                        # ZIP download for all files
                        if len(processed_files) > 1:
                            st.write("**Télécharger tous les fichiers:**")
                            
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
        📌 **Instructions d'utilisation:**
        
        1. Chargez un ou plusieurs fichiers XML contenant vos contrats de travail
        2. L'application analysera automatiquement les contrats
        3. Choisissez de traiter tous les contrats ou sélectionnez ceux à modifier
        4. Téléchargez les fichiers corrigés avec la balise HISTORIQUE ajoutée
        
        La balise `<HISTORIQUE>1</HISTORIQUE>` sera ajoutée automatiquement entre 
        `<STATUT_SALARIE>` et `<CONTDET_1>` pour chaque contrat qui n'en possède pas.
        """)
        
        # Example
        with st.expander("📋 Voir un exemple"):
            st.code("""
<STATUT_SALARIE>0</STATUT_SALARIE>
<HISTORIQUE>1</HISTORIQUE>  <!-- Balise ajoutée automatiquement -->
<CONTDET_1>
    ...
</CONTDET_1>
            """, language="xml")

if __name__ == "__main__":
    main()
