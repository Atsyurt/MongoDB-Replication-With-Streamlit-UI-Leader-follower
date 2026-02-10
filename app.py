import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import time
from datetime import datetime

st.set_page_config(page_title="MongoDB Replica Set Test", layout="wide")
st.title("🔄 MongoDB Leader-Follower (Replica Set) Test Uygulaması")

# MongoDB bağlantısı
@st.cache_resource
def get_mongo_client():
    try:
        # Docker içinden bağlanıyorsak environment variable kullan, değilse localhost
        import os
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true')
        
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000
        )
        return client
    except Exception as e:
        st.error(f"MongoDB bağlantı hatası: {e}")
        return None

def get_replica_status(client):
    """Replica set durumunu öğren"""
    try:
        admin_db = client.admin
        status = admin_db.command("replSetGetStatus")
        
        members = []
        for member in status['members']:
            members.append({
                'name': member['name'],
                'state': member['stateStr'],
                'health': '✅ Sağlıklı' if member['health'] == 1 else '❌ Sorunlu',
                'uptime': f"{member.get('uptime', 0)} saniye"
            })
        
        return members, status['set']
    except Exception as e:
        return None, str(e)

def insert_sample_data(db, collection_name, message):
    """Örnek veri ekle"""
    try:
        collection = db[collection_name]
        doc = {
            'message': message,
            'timestamp': datetime.now(),
            'counter': collection.count_documents({}) + 1
        }
        result = collection.insert_one(doc)
        return True, result.inserted_id
    except Exception as e:
        return False, str(e)

def get_all_collections(db):
    """Tüm collection'ları listele - SECONDARY'den okur"""
    from pymongo import ReadPreference
    try:
        db_secondary = db.client.get_database(db.name, read_preference=ReadPreference.SECONDARY_PREFERRED)
        collections = db_secondary.list_collection_names()
        return collections
    except Exception as e:
        st.error(f"Collection listesi alınamadı: {e}")
        return []

def read_collection_data(db, collection_name, limit=20):
    """Belirli bir collection'dan veri oku - SECONDARY'den okur"""
    from pymongo import ReadPreference
    try:
        # SECONDARY_PREFERRED: Önce follower'lardan oku, yoksa leader'dan
        db_secondary = db.client.get_database(db.name, read_preference=ReadPreference.SECONDARY_PREFERRED)
        collection = db_secondary[collection_name]
        
        # Toplam kayıt sayısı
        total_count = collection.count_documents({})
        
        # Son kayıtları getir (timestamp varsa ona göre, yoksa _id'ye göre)
        try:
            docs = list(collection.find().sort('timestamp', -1).limit(limit))
        except:
            docs = list(collection.find().sort('_id', -1).limit(limit))
        
        return docs, total_count
    except Exception as e:
        st.error(f"Okuma hatası: {e}")
        return [], 0

def test_read_preference(client, db_name):
    """Farklı read preference'ları test et"""
    from pymongo import ReadPreference
    
    results = {}
    preferences = {
        'PRIMARY': ReadPreference.PRIMARY,
        'SECONDARY': ReadPreference.SECONDARY,
        'PRIMARY_PREFERRED': ReadPreference.PRIMARY_PREFERRED,
        'SECONDARY_PREFERRED': ReadPreference.SECONDARY_PREFERRED,
    }
    
    for pref_name, pref in preferences.items():
        try:
            db = client.get_database(db_name, read_preference=pref)
            start = time.time()
            count = db.test_collection.count_documents({})
            elapsed = time.time() - start
            results[pref_name] = {
                'success': True,
                'count': count,
                'time': f"{elapsed*1000:.2f}ms"
            }
        except Exception as e:
            results[pref_name] = {
                'success': False,
                'error': str(e)
            }
    
    return results

# UI
client = get_mongo_client()

if client:
    # Sidebar - Replica Set Durumu
    with st.sidebar:
        st.header("📊 Replica Set Durumu")
        
        if st.button("🔄 Yenile", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()
        
        members, rs_name = get_replica_status(client)
        
        if members:
            st.success(f"**Replica Set:** {rs_name}")
            st.divider()
            
            for member in members:
                if 'PRIMARY' in member['state']:
                    st.success(f"👑 **{member['name']}**")
                    st.write(f"**Rol:** LEADER (PRIMARY)")
                elif 'SECONDARY' in member['state']:
                    st.info(f"📦 **{member['name']}**")
                    st.write(f"**Rol:** FOLLOWER (SECONDARY)")
                else:
                    st.warning(f"⚠️ **{member['name']}**")
                    st.write(f"**Rol:** {member['state']}")
                
                st.write(f"{member['health']} | {member['uptime']}")
                st.divider()
        else:
            st.error("❌ Replica set durumu alınamadı!")
            st.code(rs_name)

    # Ana içerik
    tab1, tab2, tab3 = st.tabs(["✍️ Veri Ekle (Write)", "📖 Veri Oku (Read)", "🧪 Read Preference Test"])
    
    with tab1:
        st.header("Veri Ekleme Testi")
        st.info("💡 Yazma işlemleri **sadece PRIMARY (LEADER)** node'a yapılır!")
        
        # Collection seçimi/oluşturma
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            db = client.test_db
            existing_collections = get_all_collections(db)
            
            # Var olan collection'lardan seç veya yeni oluştur
            collection_option = st.radio(
                "Collection:",
                ["Mevcut collection'dan seç", "Yeni collection oluştur"],
                horizontal=True
            )
            
            if collection_option == "Mevcut collection'dan seç":
                if existing_collections:
                    selected_collection = st.selectbox(
                        "Collection seçin:",
                        existing_collections,
                        index=0 if 'test_collection' not in existing_collections else existing_collections.index('test_collection')
                    )
                else:
                    st.warning("Henüz collection yok. Yeni oluşturun.")
                    selected_collection = st.text_input("Yeni collection adı:", value="test_collection")
            else:
                selected_collection = st.text_input("Yeni collection adı:", placeholder="ornek_collection")
        
        with col_b:
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            if selected_collection:
                st.info(f"📁 **{selected_collection}**")
        
        st.divider()
        
        # Veri ekleme
        col1, col2 = st.columns([3, 1])
        
        with col1:
            message = st.text_input("Mesaj girin:", placeholder="Test mesajınızı yazın...")
        
        with col2:
            st.write("")
            st.write("")
            if st.button("📝 Veri Ekle", type="primary", use_container_width=True):
                if message and selected_collection:
                    success, result = insert_sample_data(db, selected_collection, message)
                    
                    if success:
                        st.success(f"✅ Veri başarıyla eklendi!")
                        st.caption(f"Collection: {selected_collection}")
                        st.caption(f"ID: {result}")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Hata: {result}")
                elif not message:
                    st.warning("Lütfen bir mesaj girin!")
                else:
                    st.warning("Lütfen bir collection seçin/oluşturun!")
    
    with tab2:
        st.header("Veri Okuma Testi")
        st.info("💡 Okuma işlemleri **SECONDARY (FOLLOWER)** node'lardan yapılır!")
        
        db = client.test_db
        
        # Collection seçme seçeneği
        col1, col2 = st.columns([3, 1])
        with col1:
            view_option = st.radio(
                "Görünüm:",
                ["Tüm collection'ları göster", "Tek collection seç"],
                horizontal=True
            )
        
        # Collection'ları listele
        collections = get_all_collections(db)
        
        if collections:
            if view_option == "Tek collection seç":
                # Tek collection seçme modu
                selected_coll = st.selectbox(
                    "Collection seçin:",
                    sorted(collections),
                    index=0
                )
                
                docs, total_count = read_collection_data(db, selected_coll, limit=50)
                
                st.subheader(f"📁 {selected_coll} ({total_count} kayıt)")
                
                if docs:
                    # Tablo formatında göster
                    for idx, doc in enumerate(docs, 1):
                        col1, col2 = st.columns([1, 4])
                        
                        with col1:
                            st.markdown(f"**#{idx}**")
                        
                        with col2:
                            # Önemli alanları vurgula
                            if 'message' in doc:
                                st.markdown(f"**Mesaj:** {doc['message']}")
                            if 'timestamp' in doc:
                                st.caption(f"🕐 {doc['timestamp']}")
                            if 'counter' in doc:
                                st.caption(f"#️⃣ Counter: {doc['counter']}")
                            
                            # Diğer alanları göster
                            other_fields = {k: v for k, v in doc.items() 
                                          if k not in ['_id', 'message', 'timestamp', 'counter']}
                            if other_fields:
                                with st.container():
                                    st.json(other_fields, expanded=False)
                            
                            # _id'yi en altta küçük göster
                            st.caption(f"ID: {doc.get('_id', 'N/A')}")
                        
                        if idx < len(docs):
                            st.divider()
                    
                    if total_count > 50:
                        st.info(f"ℹ️ İlk 50 kayıt gösteriliyor. Toplam: {total_count}")
                else:
                    st.warning("Bu collection'da veri yok.")
            
            else:
                # Tüm collection'ları göster modu
                st.subheader(f"📚 Veritabanındaki Collection'lar ({len(collections)})")
                
                # Her collection için ayrı expander
                for coll_name in sorted(collections):
                    docs, total_count = read_collection_data(db, coll_name, limit=20)
                    
                    with st.expander(f"📁 **{coll_name}** ({total_count} kayıt)", expanded=(coll_name == 'test_collection')):
                        if docs:
                            # Tablo formatında göster
                            for idx, doc in enumerate(docs, 1):
                                col1, col2 = st.columns([1, 4])
                                
                                with col1:
                                    st.markdown(f"**#{idx}**")
                                
                                with col2:
                                    # Document'ı daha okunabilir göster
                                    display_doc = {}
                                    for key, value in doc.items():
                                        if key != '_id':  # _id'yi daha sonra ekleyelim
                                            display_doc[key] = value
                                    
                                    # Önemli alanları vurgula
                                    if 'message' in doc:
                                        st.markdown(f"**Mesaj:** {doc['message']}")
                                    if 'timestamp' in doc:
                                        st.caption(f"🕐 {doc['timestamp']}")
                                    if 'counter' in doc:
                                        st.caption(f"#️⃣ Counter: {doc['counter']}")
                                    
                                    # Diğer alanları göster
                                    other_fields = {k: v for k, v in doc.items() 
                                                  if k not in ['_id', 'message', 'timestamp', 'counter']}
                                    if other_fields:
                                        with st.container():
                                            st.json(other_fields, expanded=False)
                                    
                                    # _id'yi en altta küçük göster
                                    st.caption(f"ID: {doc.get('_id', 'N/A')}")
                                
                                if idx < len(docs):
                                    st.divider()
                            
                            if total_count > 20:
                                st.info(f"ℹ️ İlk 20 kayıt gösteriliyor. Toplam: {total_count}")
                        else:
                            st.warning("Bu collection'da veri yok.")
        else:
            st.warning("Henüz hiç collection yok. Yukarıdaki 'Veri Ekle' sekmesinden veri ekleyin!")
    
    with tab3:
        st.header("Read Preference Testi")
        st.info("💡 MongoDB'nin farklı okuma tercihlerini test edin")
        
        if st.button("🧪 Testi Başlat", type="primary"):
            with st.spinner("Test ediliyor..."):
                results = test_read_preference(client, 'test_db')
                
                st.subheader("Test Sonuçları:")
                
                for pref, result in results.items():
                    with st.expander(f"**{pref}**", expanded=True):
                        if result['success']:
                            st.success(f"✅ Başarılı")
                            st.write(f"Kayıt sayısı: {result['count']}")
                            st.write(f"Süre: {result['time']}")
                        else:
                            st.error(f"❌ Başarısız")
                            st.code(result['error'])
                
                st.divider()
                st.markdown("""
                **Read Preference Açıklamaları:**
                - **PRIMARY**: Sadece leader'dan okur (varsayılan)
                - **SECONDARY**: Sadece follower'lardan okur
                - **PRIMARY_PREFERRED**: Önce leader, yoksa follower
                - **SECONDARY_PREFERRED**: Önce follower, yoksa leader
                """)
    
    # Alt bilgi
    st.divider()
    st.caption("💡 **Test Senaryosu:** Leader node'u durdurup follower'ların yeni leader seçmesini izleyebilirsiniz: `docker stop mongo1`")

else:
    st.error("❌ MongoDB'ye bağlanılamadı! Docker konteynerlerinin çalıştığından emin olun.")
    st.code("docker-compose up -d")
