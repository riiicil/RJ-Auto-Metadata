# src/metadata/categories/for_adobestock.py

def map_to_adobe_stock_category(title, description, tags):
    """
    Memetakan metadata ke kategori Adobe Stock.
    
    Args:
        title: Judul gambar/video
        description: Deskripsi gambar/video
        tags: Daftar tag/keyword
        
    Returns:
        String ID kategori Adobe Stock yang sesuai
    """
    keywords = [tag.lower() for tag in tags]
    title_lower = title.lower()
    desc_lower = description.lower()
    
    categories = {
        "1": {"animal", "wildlife", "pet", "dog", "cat", "bird", "zoo", "fish", "insect"},
        "2": {"building", "architecture", "house", "skyscraper", "tower", "bridge", "construction"},
        "3": {"business", "office", "work", "professional", "corporate", "meeting", "finance"},
        "4": {"drink", "beverage", "cocktail", "coffee", "tea", "wine", "beer", "juice"},
        "5": {"environment", "nature", "ecology", "green", "sustainability", "climate"},
        "6": {"mind", "emotion", "feeling", "psychology", "mental", "mood", "expression"},
        "7": {"food", "meal", "cuisine", "dish", "cooking", "restaurant", "kitchen", "chef"},
        "8": {"graphic", "design", "abstract", "pattern", "texture", "background", "wallpaper"},
        "9": {"hobby", "leisure", "recreation", "entertainment", "fun", "game", "activity"},
        "10": {"industry", "factory", "manufacturing", "production", "machinery", "industrial"},
        "11": {"landscape", "scenery", "vista", "panorama", "mountain", "sea", "beach", "sky"},
        "12": {"lifestyle", "living", "daily", "routine", "home", "family", "domestic"},
        "13": {"people", "person", "human", "man", "woman", "child", "portrait", "face"},
        "14": {"plant", "flower", "tree", "garden", "botanical", "floral", "leaf", "forest"},
        "15": {"culture", "religion", "tradition", "ritual", "ceremony", "belief", "faith"},
        "16": {"science", "research", "laboratory", "experiment", "technology", "innovation"},
        "17": {"social", "issue", "problem", "society", "community", "political", "protest"},
        "18": {"sport", "athletic", "game", "competition", "match", "fitness", "exercise"},
        "19": {"technology", "digital", "computer", "electronic", "device", "gadget", "tech"},
        "20": {"transport", "vehicle", "car", "train", "airplane", "ship", "traffic", "travel"},
        "21": {"travel", "tourism", "vacation", "holiday", "trip", "journey", "destination"}
    }
    
    category_scores = {cat_id: 0 for cat_id in categories}
    
    # Skor berdasarkan keyword
    for cat_id, cat_keywords in categories.items():
        for kw in keywords:
            if any(cat_kw in kw for cat_kw in cat_keywords):
                category_scores[cat_id] += 3
    
    # Skor berdasarkan judul (lebih penting)
    for cat_id, cat_keywords in categories.items():
        if any(cat_kw in title_lower for cat_kw in cat_keywords):
            category_scores[cat_id] += 5 
    
    # Skor berdasarkan deskripsi
    for cat_id, cat_keywords in categories.items():
        if any(cat_kw in desc_lower for cat_kw in cat_keywords):
            category_scores[cat_id] += 1
    
    # Pilih kategori dengan skor tertinggi
    best_category = max(category_scores.items(), key=lambda x: x[1])
    
    if best_category[1] == 0:
        return ""
    
    return best_category[0]