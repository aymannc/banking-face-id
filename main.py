from _facenet import calc_dist

while True:
    name1 = input('name1 : ')
    name2 = input('name2 : ')
    calculated_distance = calc_dist(name1, name2)
    print(calculated_distance, 'Same' if calculated_distance <= 0.55 else 'Different', 'person\n')
