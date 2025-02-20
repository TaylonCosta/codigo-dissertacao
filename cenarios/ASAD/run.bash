for f in *.yaml; do
	python ../../main.py --modelo --heuristica -c "$f"
done
