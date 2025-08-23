pushd $(dirname $0)
for file in $(find data/ -name "*.json")
do
    target=$(echo ${file} | sed 's/data\///g' | sed 's/\.json//g')
    target="output/${target}"
    mkdir -p $(dirname "${target}")
    make "${target}.png"
    make "${target}_mini.png"
done
popd
