
//programs menu
$(function(){
	$('td.menu').hover(function(){
		var x = $(this).find('div.menu > div');
		if(!x.hasClass('shown')){
			x.slideDown(200,function(){
				x.addClass('shown');
			});
		}
	},function(ev){
		var x = $('div.menu > div.shown');
		var td = $(this);
		var tdr = td.offset().left+td.width();
		var off = x.offset();
		if(ev.pageX<off.left || ev.pageX>(off.left+x.width()) || ev.pageY>(off.top+x.height()) || (ev.pageY<60 && ev.pageX>tdr)){
			x.slideUp(200,function(){
				x.removeClass('shown');
			});
		}
	})
	//ios support
	.click(function(){
		var x = $(this).find('div.menu > div');
		if(x.hasClass('shown')){
			x.slideUp(200,function(){
				x.removeClass('shown');
			});
		}
		else{
			x.slideDown(200,function(){
				x.addClass('shown');
			});
		}
	})
	;
});

//email obfuscation
$(function(){
	$('a[data-mail]').each(function(){
		var a = $(this);
		var email = atob(a.attr('data-mail'));
		a.text(email);
		a.attr('href','mailto:'+email)
	});
})