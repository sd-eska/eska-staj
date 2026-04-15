from unittest.mock import patch
class Model:
    def _iys_consent_items(self):
        return []

m = Model()
with patch.object(type(m), '_iys_consent_items') as mock_method:
    mock_method.return_value = [1,2,3]
    print(m._iys_consent_items())
