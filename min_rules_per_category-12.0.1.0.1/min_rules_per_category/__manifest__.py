# -*- coding: utf-8 -*-
{
    "name": "Reordering Rules Per Categories",
    "version": "12.0.1.0.1",
    "category": "Warehouse",
    "author": "Odoo Tools",
    "website": "https://odootools.com/apps/12.0/reordering-rules-per-categories-376",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "stock"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_categ_order_point.xml",
        "views/stock_warehouse_orderpoint.xml",
        "data/data.xml"
    ],
    "qweb": [
        
    ],
    "js": [
        
    ],
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "The tool to prepare re-ordering rules per product categories",
    "description": """
    When you have a lot of products, especially generic ones, it becomes a challenge to generate and keep topical re-ordering rules. This tool solves the issue. The app let you assign minimum stock rules per product categories. Batch and accurate updates save your time and diminish risks of human factors.

    Stocks by product category not per each individual item
    Super fast batch creation of minimum stock rules
    Reordering rules as soon as you create or update a product
    Manual re-ordering rules are still possible
    # How reordering rules per categories work
    <p style='font-size:18px;'>Categories' rules are not themselves involved in the Odoo procurement process, but they serve as a configuration object to prepare standard rules in a batch. In such a way warehouse work flows are not interrupted by extra checks.</p>
<p style='font-size:18px;'>All you need is to create a new rule for this product category, and each of its storable items would have a stock rule with the same minimum and maximum quantities, a quantity multiple factor, a warehouse and a location, a procurement group and a company. The process is the same as when you prepare standard re-ordering levels, but it is hundreds times faster from a user perspective.</p>
<p style='font-size:18px;'>Take into that rules per categories do not consider hierarchy of categories. Rules should be set up for each category to make sure that there are no conflicts between various guidelines. For example, if a chair belongs to 'All / Office Furniture' its minimum stock rule is taken from this category rule, but it is not taken from rules for the 'All' category.</p>
    # Scenarios when minimum stock rules are updated
    <ul style='font-size:18px;'>
<li><i>A user creates a new product or add a new attribute</i>. As soon as a new storable variant is generated, the tool would consider its category rules. If any of those exist, Odoo would prepare a new reordering level for this variant.</li>
<li><i>A user updates product category of a variant</i>. In such a case Odoo would deactivate rules linked to a previous category, and prepare new rules based on an updated one. <i>It is really super fast to change minimum stock levels for all variants of this template by mere changing its category!</i></li>
<li><i>A user deactivates manual minimum stock rule</i>. Manual rules have higher priority than categories' rules. Since manual rule does not exist any more, there is a need to switch to an auto rule. Odoo would do that without any user interaction.</li>
<li><i>A user prepares a new category rule for this location</i>. Then, Odoo would update all variants within  this category beside ones which have manual rules. Take into account there might be only one rule per a combination of a product category and a stock location.</li>
<li><i>You decide to cancel all rules for this product category</i>. No problem! Just delete a related rule, and all items' rules would be also deactivated.</li>
</ul>
    Minimum stock rules per product category and location
    Assign a rule per each category-location combination
    Auto variant rules according to its category
    Different scenarios to update product re-ordering rules fast and accurate
    Make manual rule per product disregarding its category
    I faced the error: QWeb2: Template 'X' not found
    <div class="knowsystem_block_title_text">
            <div class="knowsystem_snippet_general" style="margin:0px auto 0px auto;width:100%;">
                <table align="center" cellspacing="0" cellpadding="0" border="0" class="knowsystem_table_styles" style="width:100%;background-color:transparent;border-collapse:separate;">
                    <tbody>
                        <tr>
                            <td width="100%" class="knowsystem_h_padding knowsystem_v_padding o_knowsystem_no_colorpicker" style="padding:20px;vertical-align:top;text-align:inherit;">
                                
                                <ol style="margin:0px 0 10px 0;list-style-type:decimal;"><li><p class="" style="margin:0px;">Restart your Odoo server and update the module</p></li><li><p class="" style="margin:0px;">Clean your browser cashe (Ctrl + Shift + R) or open Odoo in a private window.</p></li></ol></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    How should I install your app?
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="line-height:120%;margin:0px 0px 10px 0px;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><ol style="margin:0px 0 10px 0;list-style-type:decimal;">
	<li><p style="margin:0px;line-height:120%;">Unzip source code of purchased tools in one of your Odoo
	add-ons directory</p>
	</li><li><p style="margin:0px;line-height:120%;">Re-start the Odoo server</p>
	</li><li><p style="margin:0px;line-height:120%;">Turn on the developer mode (technical settings)</p>
	</li><li><p style="margin:0px;line-height:120%;">Update the apps' list (the apps' menu)</p>
	</li><li><p style="margin:0px;line-height:120%;">Find the app and push the button 'Install'</p>
	</li><li><p style="margin:0px;line-height:120%;">Follow the guidelines on the app's page if those exist.</p>
</li></ol>
    May I buy your app from your company directly?
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="margin:0px 0px 10px 0px;">Sorry, but no. We distribute the
tools only through the <a href="https://apps.odoo.com/apps" style="text-decoration:none;color:rgb(13, 103, 89);background-color:transparent;">official Odoo apps store</a></p>
    Your tool has dependencies on other app(s). Should I purchase those?
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="margin:0px 0px 0.25cm 0px;line-height:120%;">Yes, all modules marked in
dependencies are absolutely required for a correct work of our tool.
Take into account that prices marked on the app page already includes
all necessary dependencies.&nbsp;&nbsp;</p>
    I noticed that your app has extra add-ons. May I purchase them afterwards?
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="margin:0px 0px 0.25cm 0px;line-height:120%;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><p style="margin:0px 0px 0.25cm 0px;line-height:120%;">Yes, sure. Take into account that Odoo
automatically adds all dependencies to a cart. You should exclude
previously purchased tools.</p>
    I would like to get a discount
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="margin:0px 0px 0.25cm 0px;line-height:120%;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><p style="margin:0px 0px 0.25cm 0px;line-height:120%;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><p style="margin:0px 0px 0.25cm 0px;line-height:120%;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><p style="margin:0px 0px 0.25cm 0px;line-height:120%;">Regretfully, we do not have a
technical possibility to provide individual prices.</p>
    What are update policies of your tools?
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="margin:0px 0px 0.25cm 0px;line-height:120%;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><p style="margin:0px 0px 0.25cm 0px;line-height:120%;">
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


</p><p style="margin:0px 0px 0.25cm 0px;line-height:120%;">According to the current Odoo store
policies, by purchasing a tool you receive rights for all current and
all future versions of the tool.</p>
    How can I install your app on Odoo.sh?
    
	
	
	<style type="text/css">
	<!--
		@page { margin: 2cm }
		p { margin-bottom: 0.25cm; line-height: 120% }
		a:link { so-language: zxx }
	-->
	</style>


<p style="margin:0px 0px 10px 0px;">As soon as you purchased the
app, the button 'Deploy on Odoo.sh' will appear on the app's page in
the Odoo store. Push this button and follow the instructions.</p>
<p style="margin:0px 0px 10px 0px;">Take into account that for paid
tools you need to have a private GIT repository linked to your
Odoo.sh projects</p>
    May I install the app on my Odoo Online (SaaS) database?
    <p style="margin:0px 0px 10px 0px;">No, third party apps can not be used on Odoo Online.</p>
""",
    "images": [
        "static/description/main.png"
    ],
    "price": "44.0",
    "currency": "EUR",
}