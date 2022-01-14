odoo.define('phd_tools.web.relational_fields', function (require) {

    var registry = require('web.field_registry');
    var RelationalFields = require('web.relational_fields');
    var core = require('web.core');
    var qweb = core.qweb;
    var StageBar = RelationalFields.FieldStatus.extend({
        _render: function () {
            var stages = [];
            stages = this.status_information.slice(0,2);
            if (this.status_information.filter(x=>x.selected == true).length > 0) {
                if (!stages.includes(this.status_information.filter(x=>x.selected == true)[0], 0))
                {
                    stages.push(this.status_information.filter(x=>x.selected == true)[0]);
                }
            }
            if (stages.length == 2) {
                stages = this.status_information.slice(0,3);
            }
            var selections = _.partition(stages, function (info) {
                return (info.selected || !info.fold);
            });
            this.$el.html(qweb.render("FieldStatus.content", {
                selection_unfolded: selections[0],
                selection_folded: selections[1],
                clickable: this.isClickable,
            }));
        },
    });

    registry
    .add('stagebar', StageBar)
});