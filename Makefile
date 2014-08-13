
define rollout
	$(eval VERSION := "$(shell sed -n '/version="[0-9.]*"$$/s/.*version="\([0-9.]*\)"/\1/p' $(PLUGIN)/addon.xml)")
	@printf "== building archive for $(PLUGIN), version $(VERSION)\n"
	@find $(PLUGIN) | zip -@ "repo/$(PLUGIN)/$(PLUGIN)-$(VERSION).zip"
	@cp $(PLUGIN)/changelog.txt repo/$(PLUGIN)/changelog-$(VERSION).txt
	@python addon_xml_generator.py
	@printf "== done\n"
endef

clean:
	@rm -f `find . -name '*pyc' -o -name '*pyo' -o -name '.DS_Store'`
	@printf "== files cleaned\n"

globocom: clean
	$(eval PLUGIN  := plugin.video.globo.com)
	$(rollout)

rollout:
	$(PLUGIN)




