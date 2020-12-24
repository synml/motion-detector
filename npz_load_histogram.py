import numpy as np

import matplotlib.pyplot as plt

normal = np.load('npz/28_error.npy')

list=[]

for i in range(254):
    list.append(i+1)

print(list)
plt.hist(normal, bins = list) # 계급값
plt.ylim([1,10])

plt.title("histogram") # 제목
plt.show() # 그래프 출력상