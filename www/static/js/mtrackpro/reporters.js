$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $('#subcounty').empty();
        $('#subcounty').append("<option value='' selected='selected'>Select Sub County</option>");
        $('#facility').empty();
        $('#facility').append("<option value='' selected='selected'>Select Health Facility</option>");
		$.get(
            '/api/v1/loc_children/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var subcounties = data;
                for(var i in subcounties){
                    val = subcounties[i]["id"];
                    txt = subcounties[i]["name"];
                    $('#subcounty').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
        $.get(
            '/api/v1/district_facilities/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var facilities = data;
                for(var i in facilities){
                    val = facilities[i]["id"];
                    txt = facilities[i]["name"];
                    $('#facility').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });

	$('#subcounty').change(function(){
        var subcountyid = $(this).val();
        if (subcountyid == '0' || subcountyid == '')
            return;
        $('#location').val(subcountyid);
        $('#facility').empty();
        $('#parish').empty();
        $('#village').find('option').remove().end();
        $('#parish').append("<option value='' selected='selected'>Select Parish</option>");
        $('#village').append("<option value='' selected='selected'>Select Village</option>");
        $('#facility').append("<option value='' selected='selected'>Select Health Facility</option>");
       	$.get(
            '/api/v1/loc_children/' + subcountyid,
            {},
            function(data){
                var parishes = data;
                for(var i in parishes){
                    val = parishes[i]['id'];
                    txt = parishes[i]['name'];
                    $('#parish').append(
                            $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
        $.get(
            '/api/v1/loc_facilities/' + subcountyid,
            {},
            function(data){
                var facilities = data;
                for(var i in facilities){
                    val = facilities[i]['id'];
                    txt = facilities[i]['name'];
                    $('#facility').append(
                            $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
	});

	/*When parish is changed*/
    $('#parish').change(function(){
        var parishid = $(this).val();
        if (parishid == '0' || parishid == '')
            return;
        $('#location').val(parishid);
        $('#village').empty();
        $('#village').append("<option value='' selected='selected'>Select Village</option>");
        $.get(
            '/api/v1/loc_children/' + parishid,
            {},
            function(data){
                var villages = data;
                for(var i in villages){
                    val = villages[i]['id'];
                    txt = villages[i]['name'];
                    $('#village').append(
                            $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });

	/*When village is changed*/
	$('#village').change(function(){
        var villageid = $(this).val();
        if (villageid == '0' || villageid == '')
            return;
        $('#location').val(villageid);
    });
});
