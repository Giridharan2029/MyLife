A = int(input())
B = int(input())
odds = []
evens = []
for i in range(A, B + 1):
    if i % 2 != 0:
        odds.append(i)
    else:
        evens.append(i)

# The mistake was here: evens should be in reverse order
evens.reverse()

res = []
for i in range(len(odds)):
    res.append(odds[i])
    if i < len(evens):
        res.append(evens[i])

print(*(res))
# 21c4091@dollartestpython3