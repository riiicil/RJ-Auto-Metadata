# src/metadata/categories/for_shutterstock.py

def map_to_shutterstock_category(title, description, tags):
    """
    Memetakan metadata ke kategori Shutterstock.
    
    Args:
        title: Judul gambar/video
        description: Deskripsi gambar/video
        tags: Daftar tag/keyword
        
    Returns:
        String nama kategori Shutterstock yang sesuai
    """
    keywords = [tag.lower() for tag in tags]
    title_lower = title.lower()
    desc_lower = description.lower()
    
    categories = {
        "Abstract": {"abstract", "pattern", "texture", "design", "geometric", "shape", "minimal"},
        "Animals/Wildlife": {"animal", "wildlife", "pet", "dog", "cat", "bird", "zoo", "fish", "insect"},
        "Arts": {"art", "painting", "drawing", "sculpture", "artistic", "creative", "canvas"},
        "Backgrounds/Textures": {"background", "texture", "pattern", "surface", "wallpaper", "backdrop"},
        "Beauty/Fashion": {"beauty", "fashion", "cosmetic", "makeup", "model", "style", "glamour"},
        "Buildings/Landmarks": {"building", "landmark", "architecture", "monument", "skyscraper", "tower"},
        "Business/Finance": {"business", "finance", "office", "corporate", "professional", "meeting"},
        "Celebrities": {"celebrity", "famous", "star", "actor", "actress", "singer", "performer"},
        "Education": {"education", "school", "classroom", "student", "teacher", "learning", "study"},
        "Food and drink": {"food", "drink", "meal", "beverage", "cuisine", "restaurant", "cooking"},
        "Healthcare/Medical": {"health", "medical", "doctor", "hospital", "medicine", "healthcare"},
        "Holidays": {"holiday", "celebration", "festival", "christmas", "party", "event", "decoration"},
        "Industrial": {"industrial", "industry", "factory", "manufacturing", "machinery", "construction"},
        "Interiors": {"interior", "room", "furniture", "home", "decoration", "house", "apartment"},
        "Miscellaneous": {"miscellaneous", "various", "assorted", "diverse", "mixed", "random"},
        "Nature": {"nature", "natural", "outdoor", "environment", "landscape", "scenic", "wilderness"},
        "Objects": {"object", "item", "thing", "product", "tool", "device", "equipment"},
        "Parks/Outdoor": {"park", "outdoor", "garden", "playground", "recreation", "field", "lawn"},
        "People": {"people", "person", "human", "man", "woman", "child", "portrait", "face"},
        "Religion": {"religion", "religious", "faith", "spiritual", "belief", "worship", "ceremony"},
        "Science": {"science", "scientific", "research", "laboratory", "experiment", "chemistry"},
        "Signs/Symbols": {"sign", "symbol", "icon", "logo", "emblem", "mark", "badge"},
        "Sports/Recreation": {"sport", "recreation", "game", "fitness", "exercise", "competition", "athlete"},
        "Technology": {"technology", "tech", "digital", "computer", "electronic", "device", "gadget"},
        "Transportation": {"transportation", "vehicle", "car", "train", "airplane", "bus", "traffic"},
        "Vintage": {"vintage", "retro", "old", "antique", "classic", "nostalgic", "historical"}
    }
    
    category_scores = {cat_name: 0 for cat_name in categories}
    
    # Skor berdasarkan keyword
    for cat_name, cat_keywords in categories.items():
        for kw in keywords:
            if any(cat_kw in kw for cat_kw in cat_keywords):
                category_scores[cat_name] += 3
    
    # Skor berdasarkan judul (lebih penting)
    for cat_name, cat_keywords in categories.items():
        if any(cat_kw in title_lower for cat_kw in cat_keywords):
            category_scores[cat_name] += 5 
    
    # Skor berdasarkan deskripsi
    for cat_name, cat_keywords in categories.items():
        if any(cat_kw in desc_lower for cat_kw in cat_keywords):
            category_scores[cat_name] += 1 
    
    # Pilih kategori dengan skor tertinggi
    best_category = max(category_scores.items(), key=lambda x: x[1])
    
    if best_category[1] == 0:
        return ""
    
    return best_category[0]