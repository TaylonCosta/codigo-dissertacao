for f in *.yaml; do
	python ../main.py -c "$f" --modelo
done
