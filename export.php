<?php
header("Content-Type: text/xml");
$start = "UI";
if (isset($_REQUEST['start'])) {
	$start = $_REQUEST['start'];
}
$output = array();
exec("python createjQueryXMLDocs.py start=$start", $output);
echo implode(array_slice($output, 1));
?>