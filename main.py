from pymongo import MongoClient

# သင့်ရဲ့ Mongo URI ကို ဒီမှာ ထည့်ပါ
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

def inspect_database():
    print(f"--- Database: {db.name} ကို စစ်ဆေးနေသည် ---")
    
    # Collection အားလုံးရဲ့ နာမည်ကို ယူမယ်
    collections = db.list_collection_names()
    
    if not collections:
        print("Collection တစ်ခုမှ မရှိသေးပါ။")
        return

    for col_name in collections:
        print(f"\n📦 Collection Name: {col_name}")
        
        # ထို Collection ထဲက sample data တစ်ခုကို ယူကြည့်မယ်
        sample = db[col_name].find_one()
        
        if sample:
            print(f"   ∟ သုံးထားတဲ့ Key (Fields) များ:")
            for key in sample.keys():
                print(f"      • {key}")
            print(f"   ∟ Sample Data: {sample}")
        else:
            print("   ∟ (ဒီ collection ထဲမှာ data မရှိသေးပါ)")

if __name__ == "__main__":
    inspect_database()

