all: $(shell ls *.plain | sed 's/$$/.fnz/')

%.plain.fnz: %.plain
	fnz -f -H -e $<
	chmod 755 $@
