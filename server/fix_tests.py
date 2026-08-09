import glob

files = glob.glob('C:/MultiVendor/tests/*.py')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace for name field in tests
    content = content.replace('"name": "New Product"', '"name": {"en": "New Product"}')
    content = content.replace('"name": "A"', '"name": {"en": "A"}')
    content = content.replace('"name": "Awesome Product"', '"name": {"en": "Awesome Product"}')
    content = content.replace('"name": "Product 1"', '"name": {"en": "Product 1"}')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
print('Tests fixed')
