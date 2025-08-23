ifdef ruina_assets
ASSET_PATH := ${ruina_assets}
else
ASSET_PATH := ./assets
endif

ifdef ruina_keywords
KEYWORD_PATH := ${ruina_keywords}
else
KEYWORD_PATH := ./assets/keywords.json
endif

.PHONY: default clean
default:
	echo 'Try doing: make output/test/degraded_shockwave.png'

clean:
	rm -rf output/

output/%_mini.png: data/%.json
	python bin/generate_card.py $< $@ -a ${ASSET_PATH} -k ${KEYWORD_PATH} -m

output/%.png: data/%.json
	python bin/generate_card.py $< $@ -a ${ASSET_PATH} -k ${KEYWORD_PATH} 
