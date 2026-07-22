import urllib.request

try:
    with urllib.request.urlopen('https://hytale.com/robots.txt') as response:
        print('HYTALE ROBOTS.TXT:')
        print(response.read().decode('utf-8'))
except Exception as e:
    print('Hytale robots error:', e)

try:
    with urllib.request.urlopen('https://modifold.com/robots.txt') as response:
        print('MODIFOLD ROBOTS.TXT:')
        print(response.read().decode('utf-8'))
except Exception as e:
    print('Modifold robots error:', e)
