# Obecně Python

#https://www.geeksforgeeks.org/getting-started-with-python-programming
#-----------------------------------------------
#datové typy
#odkaz třeba zde https://www.geeksforgeeks.org/python-data-types/
#-----------------------------------------------
#Integer
a = int(3)
b = 70000
c = 0x55

#float
p = float(3.14159265)
x = 2.7182

#complex
k = 2+5j
l = complex(2)
#-----------------------------------------------
#Boolean
b = bool(True)
b = a.is_integer()
#-----------------------------------------------
#řetězec
s = "test"
s.capitalize()
s = s + " python"
ch = s[0]
type(s)
ss = str(565)

#seznam (list)
k = []
l = ['po','ut','st','ct','pa','so','ne']
k.extend(l)
l = l+['os']
l[-1]

#ntice (tuple)
t = ()
r = (1,2,3)
R = tuple(l)
R[-2]
#-----------------------------------------------
#množina (set)
st0 = set()
st1 = set(R)
st2 = set((1,2,"po", complex(3j)))
st3 = st1.intersection(st2)
st4 = st1.union(st2)

for i in st4:
    print(i,end=" ")

#-----------------------------------------------
#slovník (dictionary)
d = {}
d1 = {1: "po", 2:"út", "name":"týden", "num":2j}
d1["name"]
d1[1]
d1.update([(19,'c')])
d1.get(1)

#-----------------------------------------------
#Aritm operátory
#https://www.geeksforgeeks.org/python-operators/

a = 2*2
a+=1

#-----------------------------------------------
#Řídící sekvence

#cyklus
for i in range(10):
    print(i)

k=0
while k<10:
    print(k)


#větvení
b = 3
if b>10:
    print("YES")
elif b>5:
    print("MAY BE")
else: 
    print("NO")

#-----------------------------------------------
#funkce

def ddd(m=6):
    a = m*5
    return a%3

ddd(64)

#-----------------------------------------------
# Třídy

class A:
    def __init__(self,_a=9):
        self.a = _a

    def get(self):
        return self.a

class B(A):
    def __init__(self,_a,_b=8):
        super().__init__(_a,_b)
        self.b = _b 
    
    def get(self):
        return self.b
    
ia = A(40)
ib = B(50)

#-----------------------------------------------
