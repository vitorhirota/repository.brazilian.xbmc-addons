
define rollout
	$(eval VERSION := "$(shell egrep '^(\s*|<addon.*)version' $(PLUGIN)/addon.xml | sed -e 's/.*version="\([0-9.]*\)\".*/\1/')")
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

sbt-thenoite: clean
	$(eval PLUGIN  := plugin.video.sbt-thenoite)
	$(rollout)

sbtvideos: clean
	$(eval PLUGIN  := plugin.video.sbtvideos)
	$(rollout)

brplay: clean
	$(eval PLUGIN  := plugin.video.brplay)
	$(rollout)
	
rollout:
	$(PLUGIN)