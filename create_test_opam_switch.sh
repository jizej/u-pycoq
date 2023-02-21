# chmod +x $HOME/pycoq/create_test_opam_switch.sh
opam switch create test 4.12.0
eval $(opam env --switch=test --set-switch)