<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/lib/bootstrap.min.css">
    <style type="text/css">
      .vertical-center {
        min-height: 100%;
        min-height: 100vh;
        display: -webkit-box;
        display: -moz-box;
        display: -ms-flexbox;
        display: -webkit-flex;
        display: flex;
        -webkit-box-align : center;
        -webkit-align-items : center;
        -moz-box-align : center;
        -ms-flex-align : center;
        align-items : center;
        width: 100%;
        -webkit-box-pack : center;
        -moz-box-pack : center;
        -ms-flex-pack : center;
        -webkit-justify-content : center;
        justify-content : center;
      }
      .right {
        float: right
      }​
    </style>
    <title>Aktuelles Wetter in Meckesheim</title>
  </head>
  <body class="container">
    <div class="vertical-center">
        <div class="panel panel-primary">
          <div class="panel-heading">
            <h3>Wetter in Meckesheim - Schatthäuser Str. 14</h3>
          </div>
          <div class="panel-body bg-info">
            <h1 class="text-primary">Temperatur <span class="right">
                {{weather['temperature']}} {{weather['temperature_unit']}}</span></h1>
            <h1 class="text-primary">Luftfeuchte<span class="right">
                {{weather['humidity']}} {{weather['humidity_unit']}}</span></h1>
            <h1 class="text-primary">Luftdruck<span class="right">
                {{weather['pressure']}} {{weather['pressure_unit']}}</span></h1>
        </div>
    </div>
  </body>
</html>