import os
import json

base_dir = os.environ.get("1C_CONFIG_DIR", r"C:\Users\Vladimir\Desktop\1C_tester")
output_file = os.environ.get("1C_INDEX_FILE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "1c_compact_index.json"))

index = {
    "Catalogs": [],
    "Documents": [],
    "AccumulationRegisters": [],
    "InformationRegisters": [],
    "Reports": []
}

if not os.path.exists(base_dir):
    print("Error: 1C_tester directory not found at:", base_dir)
    print("Please set the environment variable 1C_CONFIG_DIR or edit this script to point to your unpacked 1C XML dump folder.")
else:
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    for category in index.keys():
        category_dir = os.path.join(base_dir, category)
        if os.path.exists(category_dir):
            for item in os.listdir(category_dir):
                # We look for xml files which represent the metadata object definition
                if item.endswith(".xml"):
                    object_name = item[:-4] # Strip '.xml'
                    index[category].append(object_name)
            index[category].sort()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("Successfully built compact 1C metadata index at:", output_file)
    print(f"Stats - Catalogs: {len(index['Catalogs'])}, Documents: {len(index['Documents'])}, AccumulationRegisters: {len(index['AccumulationRegisters'])}, InformationRegisters: {len(index['InformationRegisters'])}")
