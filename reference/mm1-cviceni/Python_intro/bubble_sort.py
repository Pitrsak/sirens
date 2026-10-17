
"""Algoritmus řazení buble-sort
- na vstupu je pole a, na výstupu je toto pole seřazené"""

a = [1,8,9,10,5, 20, 16, 4]
print(f"Vstupni pole: {a}")

#Prohození dvou prvků pole
def swap(a,i1,i2):
    x = a[i1]; a[i1] = a[i2]; a[i2] = x

changes = True
#Dokud byly prováděny nějaké změny v poli, pokračuj
while changes:
    changes = False
    for i in range(len(a)-1):
        if a[i]>a[i+1]:
            #pokud je prvek i větší než prvek i+1, prohodí se
            changes = True
            swap(a,i,i+1)

print(f"Výstupní pole: {a}")